#This macro semi-automates the organization of files from the Traction Force Microscope
#By Nadia Ayad, V3 February 2022
#@Boolean(label = "Run in headless mode", value=False, persist=False) HEADLESS
#@LogService log

from ij import IJ, ImagePlus, ImageStack, Prefs
import json

#from histogram2 import HistogramMatcher
import os
from ij.gui import WaitForUserDialog

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.plugins import LociExporter
from loci.plugins.out import Exporter
from ij.io import FileSaver
from loci.formats import ImageReader, MetadataTools, ImageWriter, FormatTools #https://forum.image.sc/t/set-bioformats-metadata-on-existing-tiff/10461/4

from ij.plugin import ChannelSplitter
from ij.plugin import ZProjector
from ij.plugin import Concatenator
from ij.plugin import HyperStackConverter
from ij.gui import GenericDialog

from ij.measure import ResultsTable

from ij import WindowManager as wm
from ij import IJ

from ij.gui import OvalRoi
from ij.plugin.frame import RoiManager
import time

#IJ.run("CLIJ Macro Extensions", "cl_device=")
#Ext.CLIJ_clear()

"""
Useful references: #https://github.com/zeiss-microscopy/OAD/blob/master/Workshops/2019_MIAP_Zeiss_OAD/06_apeer_module_creation/fiji_module_template/Fiji_Python_Tutorial%20-%20Create%20your%20own%20module.md
Used to create run function
"""
import errno    
import os
def mkdir_p(path): #https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
#This function will allow you to create a directory and not give an error if the directory already exists
    try:
        os.makedirs(path)
    except OSError as exc:  # Python ≥ 2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        # possibly handle other errno cases here, otherwise finally:
        else:
            raise
            
def run(imagefile, useBF=True, series=0):
	#log.info('Image Filename : ' +imagefile) # Doesnt work, cant figure out why
	if not useBF:
    	# using IJ static method
    		imp = IJ.openImage(imagefile)
	if useBF:
		# initialize the importer options
		stackview = "stackFormat=Hyperstack stackOrder=XYCZT z_begin=1 z_end=1 z_step=1 t_begin=1 t_end=49 t_step=1 "
		#openrange = "z_begin=1 z_end=1 z_step=1 t_begin=1 t_end=49 t_step=1 "
		options = ImporterOptions()
		options.setOpenAllSeries(True)
		options.setShowOMEXML(False)
		options.setConcatenate(True)
		options.setAutoscale(True)
		options.setId(imagefile)

		
		#options.setSpecifyRanges (True)
		#options.getSpecifyRangesInfo()
		#options.isSpecifyRanges()
		

        # open the ImgPlus
        print("Trying to open your image, gimme a sec...")
        imps = BF.openImagePlus(options)
        imp = imps[series] #With this option, you could change it if there are several series/file, just loop i with run (imp, series = i)
	return imp

def getShape(imp):
	try:
		channel_no = imp.getNChannels()
	except:
		channel_no = 1
	try:
		slice_no = imp.getNSlices()
	except:
		slice_no = 1
	try:
		frame_no = imp.getNFrames()
	except:
		frame_no = 1
	
	return channel_no, slice_no, frame_no

def getMaxProjection(imp):
#This function will give you the max projection of a zstack
	imp_max = ZProjector.run(imp,"max all")
	return imp_max


def do_shadingcorrection(imp, imp_shade):
	#Shading image name CANNOT have spaces in it. Change accordingly
	
	IJ.run("Set Measurements...", "mean redirect=None decimal=3");
	
	table = ResultsTable.getResultsTable()
	ResultsTable.reset(table)
	IJ.run(imp_shade, "Select All", "")
	IJ.run(imp_shade, "Measure", "")

	table.show("Results")
	Mean_index = table.getColumnIndex("Mean")
	mean = table.getColumn(Mean_index)
	mean_shade = mean[0]
	ResultsTable.reset(table)
	FileName_imp = imp.getTitle()
	FileName_impshade = imp_shade.getTitle()

	print(FileName_imp)
	IJ.run("Calculator Plus", "i1={} i2={} operation=[Divide: i2 = (i1/i2) x k1 + k2] k1={} k2=0 create".format(FileName_imp, FileName_impshade, mean_shade))
	imp_result = wm.getImage("Result")
	
	imp_shade.close()

	return imp_result


def fileorder (srcDir, maxProj, shading):
	"""
	Will find one image and split it in folders according to channel
	Need to have one Raw Images folder with all images!!!!!!
	"""
	
	pathRawFolders = [d for d, dirs, files in os.walk(srcDir)  if 'Raw' in d]
	print("All raw folders {}".format(pathRawFolders))
	
	if shading:
		pathShading =[os.path.join(d, x) for d, dirs, files in os.walk(srcDir) for x in files if 'Shading' in x]
		shading_dict = {path_channel: shadepath for i, path_channel in enumerate(path_channel) for shadepath in pathShading if ('Channel_'+str(i+1)) in shadepath} 
		print(shading_dict)
	
	
	for rawfolder in pathRawFolders:
		pathRaw = [os.path.join(d, x) for d, dirs, files in os.walk(rawfolder) for x in files]
		print("Raw files {}".format(pathRaw))
		
		sampleimg = run(pathRaw[0])

		channel_no, slice_no, frame_no = getShape(sampleimg) #The 1st image MUST be the same shape as all other in the folder!!!
		print(channel_no, slice_no, frame_no)

		if channel_no == 1 and slice_no ==1 and frame_no>1:
			sampleimg = HyperStackConverter.toHyperStack(sampleimg, frame_no, 1, 1, "Color")
			channel_no, slice_no, frame_no = getShape(sampleimg)

		#In this loop, a folder will be created for each color channel. Could switch it to create a folder per slice or timepoint by changing the variable inside range
		#path_channel = [os.path.join(srcDir, ("Channel_"+str(i+1))) for i in range(channel_no)]
		
		path_channel = [os.path.join(os.path.dirname(rawfolder), (str(i+1)+"_Channel_"+str(i+1))) for i in range(channel_no)]
		path_channel_BkgCorr = [os.path.join(os.path.dirname(rawfolder), (str(i+1)+"_Channel_"+str(i+1)+"_BkgCorr")) for i in range(channel_no)]
		
		for path in path_channel:
			print("Folders being created {}".format(path))
			mkdir_p(path)
		for path in path_channel_BkgCorr:
			print("Folders being created {}".format(path))
			mkdir_p(path)
		
		for i in range (0,len(pathRaw)):
			print("Opening image {} of {}".format(i+1, len(pathRaw)))
			imp1 = run(pathRaw[i])
			channel_no, slice_no, frame_no = getShape(imp1) 
			if channel_no == 1 and slice_no == 1 and frame_no>1:
				imp1 = HyperStackConverter.toHyperStack(imp1, frame_no, 1, 1, "Color")
			FileName1 = imp1.getTitle()
			FileName1 = FileName1.replace('.nd2', '') #remove string .nd2 from filename
			print(pathRaw[i], FileName1)
	
			
			
			chSp = ChannelSplitter()
			imps = chSp.split(imp1)
			for j in range (len(imps)):
			
				if maxProj:
					IJ.saveAs(imps[j], "Tiff",path_channel[j]+"\\"+FileName1+"_Ch"+str(j))
					imps[j] = getMaxProjection(imps[j]) #MaxProjection of a zstack
					IJ.saveAs(imps[j], "Tiff",path_channel[j]+"\\"+FileName1+"_Ch"+str(j)+"_MAX")
					print("Max Projection DONE!")
					imps[j].close()
				
				if shading:
					imps[j].show()
					imp_shade = run(shading_dict[path_channel[j]])
					imp_shade.show()
					imp_result = do_shadingcorrection(imps[j], imp_shade)
					IJ.saveAs(imp_result, "Tiff",path_channel[j]+"\\"+FileName1+"_Ch"+str(j)+"_Shaded")
					imp_result.close()
					IJ.saveAs(imps[j], "Tiff",path_channel[j]+"\\"+FileName1+"_Ch"+str(j))
					imps[j].close()
				else:
					IJ.saveAs(imps[j], "Tiff",path_channel[j]+"\\"+FileName1+"_Ch"+str(j))
					IJ.run(imps[j], "Pseudo flat field correction", "blurring=50 hide stack");
					IJ.run(imps[j], "Subtract Background...", "rolling=50 stack");
					IJ.saveAs(imps[j], "Tiff",path_channel_BkgCorr[j]+"\\"+FileName1+"_Ch"+str(j)+"_BkgCorr")
		
#Set input directory and RUN PROGRAM...
srcDir = IJ.getDirectory("Source Images for reference")

print "Source directory: ", srcDir

gui = GenericDialog("File Ordering")

gui.addChoice("Do you want to do a Max Projection on each channel?",["Yes", "No"],"No")
gui.addChoice("Do you want to use Shading Correction?",["Yes", "No"],"No");
gui.showDialog()

if gui.wasOKed():
	maxProjChoice = gui.getNextChoice()
	shadingChoice = gui.getNextChoice()
	if (maxProjChoice=="Yes"): maxProj = True
	if (maxProjChoice=="No"): maxProj = False
	if (shadingChoice=="Yes"): shading = True
	if (shadingChoice=="No"): shading = False

fileorder(srcDir, maxProj = maxProj, shading = shading)
print("Done :D")
