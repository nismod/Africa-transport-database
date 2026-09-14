# Create road segments linestring and Buffered Road Sections with metrics
# Outputs facilitate calculation of summary metrics by joins with exiting linesttrings in AFTr-DB using attribute "id2"
# Summarising road gradients using this method is better alternative to previous method

library(sf)
library(terra)
library(dplyr)
library(lwgeom) # for st_linesubstring function
library(exactextractr)

# ----------------------------
# 1. Bring in Data
# ----------------------------
elevation <- rast("D:\\Data\\GEE Africa\\Af_elevation.tif")
slope  <- rast("D:\\Data\\GEE Africa\\Af_slope.tif")
aspect <- rast("D:\\Data\\GEE Africa\\Af_aspect.tif")

DB <- "D:\\RIDE_Project\\AfTS-Db.gpkg"
roads_seg <- st_read(DB, layer = "roads_with_gradient2") |> select(id2, geometry = geom)

# ----------------------------
# 2. Project to EPSG: 27701 (Manual method required as not on PROJ database)
# ----------------------------
africa_crs <- "+proj=aeqd +lat_0=8.5 +lon_0=21.5 +x_0=5621452.02 +y_0=5990638.423 +datum=WGS84 +units=m +no_defs +type=crs"
roads_seg <- st_transform(roads_seg, africa_crs)
st_write(roads_seg, "D:/RIDE_Project/roads_projected.gpkg",layer = "roads_projected", delete_dsn = TRUE)

target_crs <- st_crs(roads_seg) # apply crs to rasters
elevation <- project(elevation, target_crs$wkt, filename = "D:/terra_temp/aspect_projected.tif", overwrite = TRUE)
slope <- project(slope, target_crs$wkt, filename = "D:/terra_temp/aspect_projected.tif", overwrite = TRUE)
aspect <- project(aspect, target_crs$wkt, filename = "D:/terra_temp/aspect_projected.tif", overwrite = TRUE)

 ----------------------------
# 3. Mask terrain rasters to road buffer (~300m)
# ----------------------------
terraOptions(tempdir = "D:/terra_temp", memfrac = 0.5, progress = 1)

road_rast <- terra::rasterize(terra::vect(roads_seg), elevation, field = 1, background = NA, touches = TRUE) 
road_rast <- terra::focal(road_rast,  w = matrix(1, nrow = 5, ncol = 5),  fun = max,  na.rm = TRUE) # 5x5 = 2 cells either side of road (road cl+300m at 150 resolution)

rasters <- list(elevation = elevation, slope = slope, aspect = aspect)
buffers <- lapply(names(rasters), function(nm) {terra::mask(rasters[[nm]], road_rast, filename = file.path("D:/RIDE_Project/terrain_buffers", paste0(nm, ".tif")),overwrite = TRUE)})

elevation <- buffers[[1]]
slope     <- buffers[[2]]
aspect    <- buffers[[3]]

# ----------------------------
# 4.1 Function - Segment roads
# ----------------------------

segment_road <- function( road,  segment_length = 150,  min_segment = 50){
  
  if( length(road)==0 ||  st_is_empty(road) ){return(NULL)}
  
  L <- as.numeric(st_length(road))

  if(L==0){ return(NULL)}

  # segment distances
  if(L <= segment_length){
    starts <- 0
    ends <- L
    
  } else {
    starts <- seq(0, L, by = segment_length)
    ends <- pmin(starts + segment_length, L)
    
    # merge short final segment
    final_length <-  ends[length(ends)] -  starts[length(starts)]

    if( final_length < min_segment){
      ends[length(ends)-1] <-  ends[length(ends)]
      starts <-  starts[-length(starts)]
      ends <- ends[-length(ends)]
    }
  }
  
  # create line substrings
  geom_list <- lapply( seq_along(starts), function(i){lwgeom::st_linesubstring( st_geometry(road), from = starts[i]/L, to = ends[i]/L)})
  
  segments <- st_sf(
    id2 = rep(road$id2, length(geom_list)),
    segment_no =  seq_along(geom_list),
    segment_id =  paste0(road$id2, "_", seq_along(geom_list)),
    start_dist =  starts,
    end_dist =  ends,
    centre_dist = (starts + ends)/2,
    geometry =  st_sfc(lapply(geom_list, function(x)x[[1]]), crs = st_crs(road))
  )
  
  segments$segment_length <- as.numeric( st_length(segments))
  
  # midpoint bearing
  bearings <- numeric( nrow(segments))
  
  for(i in seq_len(nrow(segments))){
    coords <- st_coordinates( segments[i,])
    mid <-  round( nrow(coords)/2 )
    p1 <- coords[max(1,mid-1),]
    p2 <- coords[min(nrow(coords),mid+1),]
    
    bearings[i] <-  (atan2(p2["X"]-p1["X"], p2["Y"]-p1["Y"]) *180/pi + 360) %% 360
  }
  
  segments$bearing <- bearings
  return(segments)
}

# ----------------------------
# 4.2 Function - Calculate segment gradient 
# ----------------------------

calculate_segment_gradient <- function( segments, elevation){
  
  cat("Calculating segment gradients...\n")
  
  start_points <- st_startpoint(segments)
  end_points   <- st_endpoint(segments)

  start_vect <- terra::vect(start_points)
  end_vect   <- terra::vect(end_points)
  
  start_z <- terra::extract( elevation, start_vect, method = "bilinear")[,2]
  end_z <- terra::extract(elevation, end_vect, method = "bilinear")[,2]
  
  segments$elev_start <- start_z
  segments$elev_end   <- end_z
  
  segments$elev_change <- end_z - start_z
  segments$gradient_pct <-  100 * segments$elev_change / segments$segment_length
  segments$gradient_abs_pct <- abs( segments$gradient_pct)

  return(segments)
}

# ----------------------------
# 4.3 Function - Create roadside buffers
# ----------------------------

create_road_buffers <- function( segments, buffer_distance = 50){
  
  sf_use_s2(FALSE)

  left <- st_buffer(segments, dist = buffer_distance, singleSide = TRUE)
  left$side <- "L"
  
  right <- st_buffer(segments, dist = -buffer_distance, singleSide = TRUE)
  right$side <- "R"

  buffers <- rbind(left, right)
  
  buffers$buffer_id <-  paste0(buffers$segment_id, "_", buffers$side)
  return(buffers)
}

# ----------------------------
# 4.4 Function - Extract terrain metrics
# ----------------------------

extract_terrain_metrics <- function( buffers, slope, elevation, chunk_size = 1000){
  
  chunks <-   split(buffers, ceiling(seq_len(nrow(buffers)) / chunk_size))

  results <- list()

  for(i in seq_along(chunks)){ 
    cat("Terrain chunk", i, "of", length(chunks), "\n")
    current <- chunks[[i]]

    slope_stats <-  exact_extract(slope,  current,  fun = function( values, coverage_fraction){
          
          data.frame(
            mean_slope =  weighted.mean(values, coverage_fraction,  na.rm=TRUE),
            max_slope =   max(values, na.rm=TRUE),
            p95_slope =   as.numeric( quantile(values, 0.95, na.rm=TRUE))
          )
        })
    
    elevation_stats <-  exact_extract(elevation, current,  fun = function(values, coverage_fraction){
          
          data.frame(
            mean_elevation =  weighted.mean( values, coverage_fraction, na.rm=TRUE),
            elevation_range =  max(values,na.rm=TRUE) - min(values,na.rm=TRUE))
        })

    out <- cbind(slope_stats, elevation_stats)
    out$buffer_id <-  current$buffer_id
    results[[i]] <- out
  }
  
  do.call(rbind, results)
}

# ----------------------------
# 4.5 Function - Extract aspect metrics
# ----------------------------

extract_aspect_metrics <- function( buffers, aspect, chunk_size = 1000){
  
  chunks <-  split( buffers, ceiling(seq_len(nrow(buffers)) /  chunk_size))

  results <- list()

  for(i in seq_along(chunks)){
    
    cat("Aspect chunk", i,"of", length(chunks), "\n")
    
    current <- chunks[[i]]
    
    stats <-  exact_extract(aspect,  current, fun=function(values, coverage_fraction){
          
          keep <- !is.na(values)
          values <- values[keep]
          
          coverage_fraction <-  coverage_fraction[keep]
          
          if(length(values)==0){return(data.frame(mean_aspect=NA, aspect_strength=NA))}
          
          radians <-  values*pi/180
          x <-  weighted.mean(sin(radians), coverage_fraction)
          y <-  weighted.mean(cos(radians), coverage_fraction)
          
          strength <-  sqrt(x^2+y^2)
          direction <-  atan2(x,y) * 180/pi
          direction <-  (direction+360)%%360
          
          data.frame(mean_aspect =  direction, aspect_strength =  strength)
        })

    stats$buffer_id <-  current$buffer_id
    results[[i]] <- stats
  }
  
  do.call(rbind,results )
}

# ----------------------------
# 4.6 Function - Calculate slope orientation
# ----------------------------

calculate_orientation <- function(buffers){
  
  aspect_diff <- function(a,b){ 
    d <- abs(a-b)    
    pmin(d, 360-d)}

  buffers <- buffers %>%  mutate(
      
      expected_aspect =  case_when( side=="L" ~ (bearing+90)%%360, side=="R" ~ (bearing-90)%%360),
      
      aspect_diff_from_norm =  aspect_diff( mean_aspect,expected_aspect),
      
      slope_orientation = case_when(
          aspect_diff_from_norm <=45 ~  "towards_road",
          aspect_diff_from_norm >=135 ~  "away_from_road",
          TRUE ~ "parallel"
        ))
  
  return(buffers)
}

# ----------------------------
# 5. Batch processing setup
# ----------------------------
# roads_seg <- roads_seg[1:5000,] # hash out if running full batch
batch_size <- 5000   # roads per batch
n_batches <- ceiling( nrow(roads_seg) / batch_size) # 450 batches at 5000 batch_size
output_dir <- "D:/RIDE_Project/road_batches"
dir.create( output_dir, showWarnings = FALSE)

# batches to process:
batches_to_run <- 51:100

# Examples:
# seq_len(n_batches) # all batches
# batches_to_run <- 1:20
# batches_to_run <- 21:n_batches
# batches_to_run <- c(4,7,12)
# batches_to_run <- 57

# ----------------------------
# 6. Process road batches
# ----------------------------

for(b in batches_to_run){

  cat("\n====================\n", "Processing batch",  b, ". Batches to process:",  n_batches, "\n====================\n")
  cat("current run: item ",match(b, batches_to_run), "out of",length(batches_to_run))
  
  # ----------------------------
  # Select roads for this batch
  # ----------------------------
  idx <- (((b-1)*batch_size)+1):  min(b*batch_size,  nrow(roads_seg))
  roads_batch <- roads_seg[idx,]

  # ----------------------------
  # Segment roads
  # ----------------------------
  segments_list <- lapply(seq_len(nrow(roads_batch)), function(i){segment_road( roads_batch[i,],  segment_length = 150, min_segment = 50)})
  road_segments <- do.call( rbind, segments_list)
  cat("Segments:",  nrow(road_segments),  "\n")

  # ----------------------------
  # Calculate gradients
  # ----------------------------
  road_segments <-  calculate_segment_gradient( road_segments,  elevation)
  
  # ----------------------------
  # Create roadside buffers
  # ----------------------------
  LR_buffers <-  create_road_buffers( road_segments,  buffer_distance = 50)
  cat(  "Buffers:",  nrow(LR_buffers),  "\n")

  # ----------------------------
  # Extract terrain
  # ----------------------------
  terrain_metrics <-  extract_terrain_metrics(  buffers = LR_buffers, slope = slope, elevation = elevation,  chunk_size = 1000)
  
  # ----------------------------
  # Extract aspect
  # ----------------------------
  aspect_metrics <-   extract_aspect_metrics(  buffers = LR_buffers,  aspect = aspect,  chunk_size = 1000)
  
  # ----------------------------
  # Join terrain metrics
  # ----------------------------
  terrain_metrics <-  terrain_metrics %>%  left_join( aspect_metrics, by="buffer_id")
  
  # ----------------------------
  # Add metrics back to buffers
  # ----------------------------
  LR_buffers <-  LR_buffers %>%  left_join(  terrain_metrics,  by="buffer_id")

  # ----------------------------
  # Orientation of adjacent slopes
  # ----------------------------
  LR_buffers <-  calculate_orientation( LR_buffers)
  
  # ----------------------------
  # Save batch
  # ----------------------------
  write.csv(  st_drop_geometry(LR_buffers),   file.path(output_dir,  paste0("terrain_batch_", b,".csv"      )), row.names = FALSE)
  st_write(  LR_buffers,file.path(output_dir, paste0("buffers_batch_", b, ".gpkg")), delete_dsn = TRUE, quiet = TRUE)
  st_write(  road_segments,file.path(output_dir, paste0("segments_batch_", b, ".gpkg")), delete_dsn = TRUE, quiet = TRUE)

  # ----------------------------
  # Clear memory
  # ----------------------------
  rm( roads_batch, segments_list,  road_segments,  LR_buffers,  terrain_metrics,  aspect_metrics)
  gc()
}

# ----------------------------
# 7.1 Combine layers
# ----------------------------

# Road Segments
segment_files <-  list.files( output_dir,  pattern = "^segments_batch_.*\\.gpkg$", full.names = TRUE)
road_segments <-  do.call(rbind, lapply( segment_files, st_read,  quiet = TRUE))
st_write(road_segments, DB,  layer = "road_segments",  delete_layer = TRUE)

# Road Buffers
buffer_files <-  list.files( output_dir,  pattern = "^buffers_batch_.*\\.gpkg$", full.names = TRUE)
LR_buffers <-  do.call( rbind, lapply( buffer_files, st_read, quiet = TRUE))
st_write(LR_buffers,DB, layer = "roadside_terrain_metrics",  delete_layer = TRUE)

# terrain tables
terrain_files <-  list.files(output_dir, pattern = "^terrain_batch_.*\\.csv$", full.names = TRUE  )
terrain_metrics <-  do.call(rbind, lapply( terrain_files, read.csv))
write.csv(terrain_metrics, file.path(output_dir, "terrain_metrics.csv"  ), row.names = FALSE)
