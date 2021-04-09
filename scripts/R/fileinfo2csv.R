

########################################
##A function to wrute file and folder volumes to a csv
##Author: Deepa S Filatow
##This function requires the fs package to be installed
install.packages(c('fs', 'dplyr')) # this line can be scipped if you already have these packages installed.


## Create a function
fileinfo2csv <- function(wd, fn) {
  
  
  ##The function file_sumamry2csv takes two inputs, a working direcotry file path, wd,  and an output file name, fn. 
  ##Then creates an output .csv file containing file information for every file in the directory.
  ##Example: file_summary2csv("H:/My Documents", "fileinfo")
  
  library (fs)
  library (dplyr)
  
  ##set the working directory and add a file extention to fn
  setwd(wd)
  fn <- paste0(fn, ".csv")
  
  if (file_exists(paste0(wd, "/", fn))==FALSE)  {
    #print a message to the console when the function starts
    print (paste0("Searching the directory ", wd, " to create a list of files and their properties."))
    
    #create the fileinfo dataframe and add/format some additional fields
    fileinfo <-dir_info(wd, fail = T, all = T, recurse = T) 
    fileinfo$size_num <- as.integer(fileinfo$size)
    fileinfo$file <- path_file(fileinfo$path)
    fileinfo$dir <- path_dir(fileinfo$path)
    
    #calclate the total file size and number of files in the target directory and print the answer to screen.
    s <- sum(fileinfo$size)
    y <- nrow(fileinfo)
    f <- nrow(dplyr::filter(fileinfo, type == "file"))
    d <- nrow(dplyr::filter(fileinfo, type == "directory"))
    print (paste0("The directory ", wd, " has a total size of ", s, " bites, ", d, " directorie(s), and ", f,  " files."))
    print (paste0("The file ", wd, "/", fn, " has been created."))
    
    #write and return the dataframe fileinfo to a csv in the root of the target directory
    return(write.table(fileinfo, sep = ",", col.names = T, row.names = F, fn))
    
  } else {
    return(print(paste0("The file ", fn,  " already exists in this directory. The opperation has been terminated. Rename your old file and try again. ")))}
  }
  
  ##BC Gov workers can uncomment the following section to test the function on their My Documents folder. You can change wd to be any folder you want to report on. 
  ##You can change fn to anything you want to name your output file name.

  #wd <- "H:/My Documents"
  #fn <- "MyDocumentsFileinfo"
  #fileinfo2csv(wd, fn)
  
  ##You can also just put the folder and file name directly into the function like this.

  #fileinfo2csv("H:/My Documents", "MyDocumentsFileinfo2")
  
