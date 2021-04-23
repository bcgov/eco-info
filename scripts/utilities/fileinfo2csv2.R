########################################
##A function to write file and folder volumes to a csv
##Author: Deepa S Filatow
##This function requires the fs and dplyr packages to be installed
install.packages(c('fs', 'dplyr')) # this line can be scipped if you already have these packages installed.


## Create a function
fileinfo2csv <- function(wd = "H:/", fn = "foldercontent") {
  
  
  ##The function file_sumamry2csv takes two inputs, a working direcotry file path, wd,  and an output file name, fn. 
  ##Then creates an output .csv file containing file information for every file in the directory.
  ##default values are set to H:/ and fileinfo. So if you run fileinfo2csv() it will put a file called 
  ##fileinfo.csv in the route of your H drive with a listing of all your H drive contents and file information including size, birth time, .
  ##Example: file_summary2csv("H:/Maps", "fileinfo")
  
  library (fs)
  library (dplyr)
  
  ##set the working directory and add a file extention to fn
  setwd(wd)
  fn <- paste0(fn, ".csv")
  start_t<-Sys.time()
  
  if (file_exists(paste0(wd, "/", fn))==FALSE)  {
    #print a message to the console when the function starts
    print (paste0("Searching the directory ", wd, " to create a list of files and their properties.", start_t))
    
    #create the fileinfo dataframe and add/format some additional fields
    fileinfo <-dir_info(wd, fail = T, all = T, recurse = T) 
    fileinfo$size_bytes <- as.double(fileinfo$size)
    fileinfo$size_mb <- as.integer(fileinfo$size_bytes*0.000001)
    fileinfo$size_gb <- as.integer(fileinfo$size_bytes * 0.000000001)
    fileinfo$file <- path_file(fileinfo$path)
    fileinfo$dir <- path_dir(fileinfo$path)
    
    #calclate the total file size and number of files in the target directory and print the answer to screen.
    s <- sum(fileinfo$size)
    y <- nrow(fileinfo)
    f <- nrow(dplyr::filter(fileinfo, type == "file"))
    d <- nrow(dplyr::filter(fileinfo, type == "directory"))
    m1 <- (paste0("The directory ", wd, " has a total size of ", s, " bites, ", d, " directorie(s), and ", f,  " files."))
    m2 <- (paste0("The file ", wd, "/", fn, " has been created."))
    finish_t <-Sys.time()
    m3 <- (paste0("run time: ", finish_t-start_t, " seconds."))
    print(paste(m1, m2, m3), sep = '')
    #write and return the dataframe fileinfo to a csv in the root of the target directory
    return(write.table(fileinfo, sep = ",", col.names = T, row.names = F, fn))
    ##have not got this next line to work yet as R only functions only return one object???? the code is correct but the line does not run
    return(cat(m1, m2, m3, file = paste0(fn, "_log.txt"), sep = '\r'))
    } 
  else {
    return(print(paste0("The file ", fn,  " already exists in this directory. The opperation has been terminated. Rename your old file and try again. ")))}}

##BC Gov workers can uncomment the following section to test the function on their My Documents folder. You can change wd to be any folder you want to report on. 
##You can change fn to anything you want to name your output file name.

#wd <- "H:/My Documents"
#fn <- "MyDocumentsFileinfo"
#fileinfo2csv(wd, fn)

##You can also just put the folder and file name directly into the function like this.

#fileinfo2csv("H:/My Documents", "MyDocumentsFileinfo2")
