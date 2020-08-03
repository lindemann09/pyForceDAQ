# Reading pyForceDAQ data
#
# read_force_data(folder, filename)
#     Note: Extract event data with convert_data.py
#           ``
#           python convert_data.py -e [FILENAME]
#           ``
#
# O. Lindemann

require(stringr)

read.force.data = function(folder, filename) {
  # Reading pyForceDAQ data
  
  path = file.path(folder, filename)
  message("reading ", path)

  idx = str_locate(path, ".csv.gz")
  if (!is.na(idx[1])) {
    ext = ".csv.gz"  
  } else {
    idx = str_locate(path, ".csv")
    ext = ".csv"
  }
  
  name = str_sub(path, start=0, end=idx[1]-1)
  events = read.csv(paste(name, ".events", ext, sep=""), 
                     comment.char="#", 
                     na.strings=c("NA", "None"))
  force = read.csv(path, 
                   comment.char="#", 
                   na.strings=c("NA", "None"))
  
  return(list(force = force, 
              events = events))
}
