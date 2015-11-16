# Reading pyForceDAQ data
#
# read_force_data(folder, filename)
#     Note: Extract non force data with Python using 
#           forceDAQ.data_handling.extract_non_force_data
#
# O. Lindemann

require(stringr)

read_force_data = function(folder, filename) {
  # Reading pyForceDAQ data
  
  path = file.path(folder, file)
  message("reading ", path)

  idx = str_locate(path, ".csv.gz")
  if (!is.na(idx[1])) {
    ext = ".csv.gz"  
  } else {
    idx = str_locate(path, ".csv")
    ext = ".csv"
  }
  
  name = str_sub(path, start=0, end=idx[1]-1)
  trigger = read.csv(paste(name, ".trigger", ext, sep=""), 
                     comment.char="#", 
                     na.strings=c("NA", "None"))
  udp = read.csv(paste(name, ".udp", ext, sep=""), 
                     comment.char="#", 
                     na.strings=c("NA", "None"))
  force = read.csv(path, 
                   comment.char="#", 
                   na.strings=c("NA", "None"))
  
  return(list(force=force, 
              trigger=trigger, 
              udp=udp))
}
