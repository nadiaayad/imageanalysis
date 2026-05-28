from ij import IJ, ImagePlus
import os
from ij.gui import WaitForUserDialog, Roi
from ij.plugin.frame import RoiManager
import math
#from java.util import ArrayList, Arrays
import csv
from ij.plugin import ChannelSplitter
from loci.plugins import BF

def folderpaths (srcDir):
	"""
	Experiments must be labelled properly.
	Each global experiment must be separated into folders (srcDir)
	where the next layer are the different dates  which represent different replicates
	Within each replicate, there should be 3 folders: Raw Folders, TIFF Images, Probabilities
	Raw images won't be manipulated
	TIFF Images will be separated into the different channels (one folder/channel)
	Probabilities are the output for ilastik which are separated the same way as the TIFF folders (one folder/channel)
	
	"""

	pathsTIFF = []
	pathsProb = []
	pathsExpDates = []

	#Using os.walk to obtain filenames and directory paths and names
	for dirpath, dirnames, filenames in os.walk(srcDir):
		for date in dirnames:
		#Datepath is the path of each experimental replicate
			datepath = os.path.join(dirpath, date)
			pathsExpDates.append(str(datepath))
			#Here the list of TIFF and Probabilities directory paths are obtained
			for d in dirnames:
				if 'Channel' in d and 'TIFF' in dirpath:
					pathsTIFF.append (str(os.path.join(dirpath, d)))
				elif 'Channel' in d and 'Probabilities' in dirpath:
					pathsProb.append(str(os.path.join(dirpath, d)))
	
	#Remove duplicates
	pathsTIFF = list( dict.fromkeys(pathsTIFF) ) 
	pathsProb = list( dict.fromkeys(pathsProb) ) 

	#With these lists, now it's easy to use os.walk and an if statement to find channel specific files (i.e. DAPI)
	
	return pathsTIFF, pathsProb, pathsExpDates
	
def threshold60x (pathdapi, path1, path2):
	listnames = []
	listnames1 = []
	listnames2 = []
	newpathdapi = pathdapi
	newpath1 = path1 + "\\"
	newpath2 = path2 
	
	# OS Walk logic remains the same to find filenames
	for (dirpath, dirnames, filenames) in os.walk(newpathdapi):
		listnames.extend(filenames)
	names = [name for name in listnames]
	
	for (dirpath, dirnames, filenames) in os.walk(newpath1):
		listnames1.extend(filenames)
	names1 = [name for name in listnames1]

	for (dirpath, dirnames, filenames) in os.walk(newpath2):
		listnames2.extend(filenames)
	names2 = [name for name in listnames2]
	
	# Loop through each image file
	for i in range(0, len(names)):
		imp0 = IJ.openImage(newpathdapi + names[i])
		stackSize = imp0.getStackSize() # Determine if it's a stack
		
		FileName = imp0.getTitle().replace(".tif","").replace(".TIF","").replace("_Probabilities","")
		pathcsv = pathdapi + "csv\\"
		if not os.path.exists(pathcsv): os.makedirs(pathcsv)

		f = open(pathcsv + FileName + ".csv", 'w')
		writer = csv.writer(f)
		# Added 'slice' to the header
		writer.writerow(['slice', 'roi_index', 'mean channel 1', 'mean channel 2']) 

		# Open reference channels
		imp1_stack = IJ.openImage(newpath1 + names1[i])
		imp2_stack = IJ.openImage(newpath2 + names2[i])

		# --- NEW STACK LOOP ---
		for k in range(1, stackSize + 1):
			print("Processing " + FileName + " Slice: " + str(k))
			
			# Get specific slice from the probability mask
			imp0.setSlice(k)
			ip_mask = imp0.getProcessor().duplicate()
			imp_temp = ImagePlus("temp", ip_mask)

			# Processing steps (Thresholding)
			IJ.run(imp_temp, "Gamma...", "value=0.70")
			IJ.run(imp_temp, "Subtract Background...", "rolling=500")
			IJ.run(imp_temp, "Minimum...", "sigma=5")
			IJ.run(imp_temp, "Median...", "sigma=10")
			IJ.run(imp_temp, "Gaussian Blur...", "sigma=5")
			IJ.run(imp_temp, "8-bit", "")
			IJ.setAutoThreshold(imp_temp, "Moments dark")
			IJ.run(imp_temp, "Convert to Mask", "")
			IJ.run(imp_temp, "Watershed", "")

			# ROI Management
			rm = RoiManager.getRoiManager()
			rm.runCommand("reset") 
			IJ.run(imp_temp, "Create Selection", "")
			
			if imp_temp.getRoi() is not None:
				rm.addRoi(imp_temp.getRoi())
				rm.runCommand(imp_temp, "Split")
				rm.select(0) # Remove the original composite ROI
				rm.runCommand("Delete")
				
				ra = rm.getRoisAsArray()

				# Get the processors for the current slice in other channels
				ip1 = imp1_stack.getStack().getProcessor(k)
				ip2 = imp2_stack.getStack().getProcessor(k)

				for j, r in enumerate(ra):
					ip1.setRoi(r)
					ip2.setRoi(r)
					stats1 = ip1.getStatistics()
					stats2 = ip2.getStatistics()
					
					writer.writerow([k, j, stats1.mean, stats2.mean])
			
			# Optional: Save thresholded stack slice by slice or skip
			# IJ.saveAs(imp_temp, "Tiff", newpathdapi + FileName + "_Slice_" + str(k) + "_Thr")

		f.close()
		imp0.close()
		imp1_stack.close()
		imp2_stack.close()
		print("Finished " + FileName)

# Execution
dapiDir = IJ.getDirectory("Folder Dapi")
ch1Dir = IJ.getDirectory("Channel1")
ch2Dir = IJ.getDirectory("Channel2")
threshold60x(dapiDir, ch1Dir, ch2Dir)
