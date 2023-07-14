#@Boolean(label = "Run in headless mode", value=False, persist=False) HEADLESS
#@LogService log

"""This macro will center the colonies, equalize intensity and crop them based on shape for a maximum of 3 channels 

By Nadia Ayad, V2 December 2021"""

from ij import IJ, ImagePlus, ImageStack, Prefs
import json

#from histogram2 import HistogramMatcher

from ij.gui import WaitForUserDialog, Roi
from ij import WindowManager as wm

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.plugins import LociExporter
from loci.plugins.out import Exporter
import loci.formats.IFormatReader
import loci.formats.ImageReader
import loci.plugins.util.ImageProcessorReader
from ij.io import FileSaver

from ij.plugin import Concatenator
from ij.plugin import ChannelSplitter
from ij.plugin import ZProjector
from ij.plugin.frame import RoiManager

from ij.gui import WaitForUserDialog, Toolbar
from ij.gui import GenericDialog

from ij.measure import ResultsTable

from java.util import ArrayList, Arrays

import time
import errno    
import os

"""
Useful references: #https://github.com/zeiss-microscopy/OAD/blob/master/Workshops/2019_MIAP_Zeiss_OAD/06_apeer_module_creation/fiji_module_template/Fiji_Python_Tutorial%20-%20Create%20your%20own%20module.md
Used to create run function
"""



def mkdir_p(path): #From: https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
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
#This function will open files through either the normal imageJ method or through BioFormats (preferred)
	#IJ.log.info('Image Filename : ' +imagefile) # Doesnt work, cant figure out why
	if not useBF:
	# using IJ static method
		imp = IJ.openImage(imagefile)
	
	if useBF:
	# initialize the importer options
		print("Using BioFormats")
		options = ImporterOptions()
		options.setOpenAllSeries(True)
		options.setShowOMEXML(False)
		options.setConcatenate(True)
		options.setAutoscale(True)
		options.setId(imagefile)
		#options.setSpecifyRanges(True)
		#options.setSeriesOn(imagefile,True)
		
        # open the ImgPlus
        imps = BF.openImagePlus(options)
        imp = imps[series] #With this option, could change it if there are several series/file, just loop i with run (imp, series = i)
        print("Giving you an opened image...")
        imp.show()
	return imp

def getMaxProjection(imp):
#This function will give you the max projection of a zstack
	imp_max = ZProjector.run(imp,"max")
	return imp_max

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

def getROIBF (imp, fldr_mask):
	#Making sure that all values are the values in pixel
	IJ.run("Set Scale...", "distance=0 known=1 unit=pixel")
	
	#Enhancing contrast of BF image
	#IJ.run(imp, "Enhance Contrast...", "saturated=0.01 equalize process_all use")	
	imp.show()

	channel_no, slice_no, frame_no = getShape(imp)
	print(channel_no, slice_no, frame_no)
	FileName = imp.getTitle()
	print("getRoiBF filename {}".format(FileName))
	
	#Selection of outline is user based
	wait = WaitForUserDialog("Center Selection","Please draw the outline of the colony")
	wait.show()
	
	roi = imp.getRoi()
	roitype = roi.getType()

	#IJ.log(roi.getType())
	#if roitype == Roi.POINT:
	#imp.setRoi(new PolygonRoi(xpoints,ypoints,3,Roi.POLYGON))
	roim = RoiManager()
	rm = roim.getRoiManager()
	rm.runCommand('reset')
	rm.addRoi(roi)

	ra = rm.getRoisAsArray()

	imp.setRoi(ra[0])
	IJ.run("Set Scale...", "distance=0 known=1 unit=pixel")
	IJ.run(imp, "Set Measurements...", "centroid redirect=None decimal=3")
	
	table = ResultsTable.getResultsTable()
	ResultsTable.reset(table)
	IJ.run(imp, "Measure", "")
	table.show("Results")
	X_index = table.getColumnIndex("X")
	centroidsx = table.getColumn(X_index)
	c_x = centroidsx[0]

	Y_index = table.getColumnIndex("Y")
	centroidsy = table.getColumn(Y_index)
	c_y = centroidsy[0]
	
	ResultsTable.reset(table)
	print("Centroid of ROI drawn x {} and y {}".format(c_x,c_y))
	
	roimask, pointsmask = getROIpoints(imp, c_x, c_y, fldr_mask)
	rm.runCommand('reset')
	impcrop = cropImage(imp, c_x, c_y, roi = 0, FileName_OG = FileName)
		
	return c_x, c_y, roimask

def getROIpoints(imp, x, y, outputDir):
	FileName = imp.getTitle()
	print("getROIpoints filename {}".format(FileName))
	
	#Creates a mask based on the ROI drawn for the area that you want to collect
	roim = RoiManager()
	rm = roim.getRoiManager()
	ra = rm.getRoisAsArray()
	imp.setRoi(ra[0])
	
	
	mask = imp.createRoiMask()
	maskImp = ImagePlus("Mask", mask)
	maskImp.show()
			
	#IJ.run(maskImp, "Maximum...", "radius=75.5") #Adding 20 um of buffer space between colony outline and edge of mask (1.55 px/um for 10x TFM, change if using different magnification/microscope)

	IJ.run(maskImp, "Select None", "")
	maskImpCrop = cropImage(maskImp, x, y, roi=0, FileName_OG = FileName)
	
	#Will select the mask created
	maskImpCrop = wm.getImage("Mask-crop")
	IJ.run(maskImpCrop, "Invert", "");
	IJ.run(maskImpCrop, "Create Selection", "")
	roi = maskImpCrop.getRoi()

	#Adding ROI to ROI manager
	rm.addRoi(roi)
	ra_2 = rm.getRoisAsArray()
	

	print("ROI {}".format(ra_2[1]))
	#Now, there are two ROIs in ROI manager. First the one created by the user 
	
	#Will get the x, y coordinates of all pixels inside the mask called points
	points = roi.getContainedPoints() #It's in the form of a java array
	#IJ.saveAs(points, "Text",outputDir+"\\"+FileName+"mask")
	FileName_base = FileName.replace(".tif","")
	IJ.saveAs(maskImpCrop, "Tiff",outputDir+"\\"+FileName_base+"_mask")
	
	maskImp.changes = False
	maskImp.close() #Comment this out if you want to see the mask created
	maskImpCrop.close()
	
	return ra_2[1], points
	
def threshold (imp):
	IJ.run(imp, "Gaussian Blur...", "sigma=2");
	IJ.setAutoThreshold(imp, "MaxEntropy dark no-reset");


def cropImage(imp, x, y, roi = 0, FileName_OG = "placeholder"):
	#Necessary to make a FileName_OG variable because stacked images after alignment lose their Filename, so in that case, a FileName is passed during the crop
	#This next FileName is the one that the passed imp has in the program (for BF images, it is the original FileName, for stacked/aligned, it will be different)
	FileName = imp.getTitle()
	
	#Making sure that no ROI is selected before crop
	IJ.run(imp, "Select None", "")
	print("For crop of file {}, center used is {}, {}".format(FileName, x,y))
	#Creating the shift for the beads unstressed image by adding the centroid of the BF to the alignment info of the stressed beads images

	if "_T" in FileName_OG or "-T" in FileName_OG:
		y = y+280
		IJ.run(imp, "Specify...", "width={} height={} x={} y={} centered".format(1950, 1750, x, y))
	else:
		IJ.run(imp, "Specify...", "width={} height={} x={} y={} centered".format(1700, 1700, x, y))
		
	
	impcrop = IJ.run(imp, "Duplicate...", "duplicate title={}-crop".format(FileName))
	impcrop = wm.getImage("{}-crop".format(FileName))

	return impcrop


def makepairs(fldr_stacksBF, fldr_masks):
	#fldr_pair is the folder in which to save the pairs
	BFstDir = IJ.getDirectory("1. Gimme the directory of the channel to crop and center")
	Ch2Dir = IJ.getDirectory("2. Gimme the directory of the channel to propagate")
	Ch3Dir = IJ.getDirectory("3. Gimme the directory of the channel to propagate if you still have another")
	Ch4Dir = IJ.getDirectory("4. Gimme the directory of the channel to propagate if you still have another")
	
	
	pathBF = [os.path.join(d, x) for d, dirs, files in os.walk(BFstDir) for x in files ]
	#Making sure that it is ordered alphabetically
	pathBF = sorted(pathBF)
	
	pathCh2 = [os.path.join(d, x) for d, dirs, files in os.walk(Ch2Dir) for x in files ]
	#Making sure that it is ordered alphabetically
	patCh2 = sorted(pathCh2)

	if Ch3Dir:
		pathCh3 = [os.path.join(d, x) for d, dirs, files in os.walk(Ch3Dir) for x in files ]
		pathCh3 = sorted(pathCh3)
		print(Ch3Dir)
		
	if Ch4Dir:
		pathCh4 = [os.path.join(d, x) for d, dirs, files in os.walk(Ch4Dir) for x in files ]
		pathCh4 = sorted(pathCh4)
		print(Ch4Dir)
	
	for i in range(0,len(pathBF)):
		print("Opening BF image {} in {}".format(i, pathBF[i]))
		imp_stack = run(pathBF[i])
		IJ.run(imp_stack, "8-bit", "")
		
		impBF = getMaxProjection(imp_stack)
		print("Max Projection DONE!")
		impBF.show()
		imp_stack.changes = False
		imp_stack.close()
		
		FileNameBF = impBF.getTitle()
		impBF = wm.getImage(FileNameBF)
		c_x, c_y, roimask = getROIBF (impBF, fldr_masks)
	
		impBF.changes = False	
		impBF.close()
		FileNameBF_base = FileNameBF.replace(".tif","")
		path_pair_BFcrop = os.path.join(fldr_stacksBF, FileNameBF_base+"-crop")
	
		impBFcrop = wm.getImage(FileNameBF+"-crop")
		IJ.saveAs(impBFcrop, "Tiff",path_pair_BFcrop)
		impBFcrop.close()


		impCh2_stack = run(pathCh2[i])
		IJ.run(impCh2_stack, "8-bit", "");
		impCh2 = getMaxProjection(impCh2_stack)
		#IJ.run(impCh2, "Enhance Contrast...", "saturated=0.01 equalize process_all use")	
		impCh2.show()
		impCh2_stack.changes = False
		impCh2_stack.close()
		FileNameCh2 = impCh2.getTitle()
		FileNameCh2_base = FileNameCh2.replace(".tif","")
		path_pair_Ch2crop = os.path.join(fldr_stacksBF, FileNameCh2_base+"-crop")
		
		impCh2crop = cropImage(impCh2, c_x, c_y, roi = 0, FileName_OG = FileNameCh2)
		IJ.saveAs(impCh2crop, "Tiff",path_pair_Ch2crop)
		impCh2.close()
		impCh2crop.close()

		if Ch3Dir:
			impCh3_stack = run(pathCh3[i])
			IJ.run(impCh3_stack, "8-bit", "");
			impCh3 = getMaxProjection(impCh3_stack)
			#IJ.run(impCh3, "Enhance Contrast...", "saturated=0.01 equalize process_all use")
			impCh3.show()
			impCh3_stack.changes = False
			impCh3_stack.close()
			FileNameCh3 = impCh3.getTitle()
			FileNameCh3_base = FileNameCh3.replace(".tif","")
			path_pair_Ch3crop = os.path.join(fldr_stacksBF, FileNameCh3_base+"-crop")
			
			impCh3crop = cropImage(impCh3, c_x, c_y, roi = 0, FileName_OG = FileNameCh3)
			IJ.saveAs(impCh3crop, "Tiff",path_pair_Ch3crop)
			impCh3.close()
			impCh3crop.close()
			
		if Ch4Dir:
			impCh4_stack = run(pathCh4[i])
			IJ.run(impCh4_stack, "8-bit", "");
			impCh4 = getMaxProjection(impCh4_stack)
			#IJ.run(impCh4, "Enhance Contrast...", "saturated=0.01 equalize process_all use")
			impCh4.show()
			impCh4_stack.changes = False
			impCh4_stack.close()
			FileNameCh4 = impCh4.getTitle()
			FileNameCh4_base = FileNameCh4.replace(".tif","")
			path_pair_Ch4crop = os.path.join(fldr_stacksBF, FileNameCh4_base+"-crop")
			
			impCh4crop = cropImage(impCh4, c_x, c_y, roi = 0, FileName_OG = FileNameCh4)
			IJ.saveAs(impCh4crop, "Tiff",path_pair_Ch4crop)
			impCh4.close()
			impCh4crop.close()
		


def function (srcDir):
	"""
	Will create folders if not existent for manipulations

	"""
	#Create Directory for stacks, masks
	fldr_stacksBF = os.path.join(srcDir, "5_Stacks_BF-edited")
	mkdir_p(fldr_stacksBF)
	fldr_masks = os.path.join(srcDir, "6_Masks")
	mkdir_p(fldr_masks)
	
	makepairs(fldr_stacksBF, fldr_masks)
	
	print("Done :D")
	
#Set input directory and RUN PROGRAM...
srcDir = IJ.getDirectory("Source Images for reference")
print "Source directory: ", srcDir
function(srcDir)








