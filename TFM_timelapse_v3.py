#@Boolean(label = "Run in headless mode", value=False, persist=False) HEADLESS
#@LogService log

"""This macro will analyze the traction forces over time from a stack of bead images. 

NEED TO HAVE ORGANIZED FILES AS SUCH:
1) SOURCE FOLDER
	1.1) UNSTRESSED BEADS FOLDER
	1.2) STRESSED BEADS OVER TIME FOLDER
	1.3) BF/CHANNEL OVER TIME FOR OUTLINE FOLDER
	1.4) ADDITIONAL CHANNEL OVER TIME FOLDER (optional)

By Nadia Ayad, V3 December 2021"""

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
	imp_max = ZProjector.run(imp,"max all")
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


def ParseTransformationMatrix():
	#Adapted from https://forum.image.sc/t/registration-of-multi-channel-timelapse-with-linear-stack-alignment-with-sift/50209/9
	#Get Log Output
	logString = IJ.getLog()
	#Subdivide into Rows
	rows=logString.split("\n")
	
	aligninfo = [] #Empty list that will have xShift, yShift for slice 1 on position 0. aligninfo[0][1] is the xShift of slice 1
	
	for i in range(len(rows)):
		if "Transformation" in rows[i]:
			xShift, yShift = ParseXY(rows[i])
			aligninfo.append([xShift, yShift])
			

	
	return aligninfo
	
def ParseXY(row):
	split1 = row.split("[")
	XSplit = split1[2].split(",")
	
	YSplit = split1[3].split(",")

	XPosTemp = str(XSplit[2])
	YPosTemp = str(YSplit[2])
	
	
	XPos = XPosTemp[0:(len(XPosTemp)-1)]
	YPos = YPosTemp[0:(len(YPosTemp)-2)]


	xShift = float(XPos)
	yShift = float(YPos)

	print("After parsing log for transformation matrix info xShift: {} and yShift: {}".format(xShift, yShift))
	return xShift, yShift


def linearalignment (imp, method):
	#Some code adapted from https://forum.image.sc/t/from-selection-to-roi-in-jython/19926/2
	
	IJ.run("Set Scale...", "distance=0 known=0 unit=pixel")
	
	if method == "Template":
		print("Starting Linear Alignment")
		imp = IJ.getImage()
		rm = RoiManager.getInstance()
		if not rm:
			rm = RoiManager()
		rm.runCommand("reset")
	
		#ask the user to define a selection and get the bounds of the selection
		IJ.setTool(Toolbar.RECTANGLE)
		WaitForUserDialog("Select the area,then click OK.").show()
		roi1 = imp.getRoi()
		imp.setRoi(roi1)
		rm.addRoi(roi1)
		
	
		rois = rm.getRoisAsArray() # this is a list of rois (only 1 as it got cleared)
		for roi in rois:
			bounds = roi.getBounds() #bounds.width, bounds.height
	
		rm.runCommand('Deselect')
		rm.runCommand('Delete')
	
		IJ.run(imp, "Align slices in stack...", "method=5 windowsizex={} windowsizey={} x0={} y0={} swindow=0 subpixel=false itpmethod=0 ref.slice=1 show=true".format(bounds.width, bounds.height, bounds.x, bounds.y))
		#save results
	
		imp.setRoi(0, 0, imp.width, imp.height)
		"""!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"""
		aligninfo = []
		return imp, aligninfo

	else:
		channel_no, slice_no, frame_no = getShape(imp)
		print(channel_no, slice_no, frame_no)
		IJ.run(imp, "8-bit", "stack")
		IJ.run(imp, "Enhance Contrast...", "saturated=0.001 equalize process_all use")
		IJ.run(imp, "Gaussian Blur...", "sigma=2 stack")	
		IJ.run(imp, "Subtract Background...", "rolling=150 stack")
		IJ.run("Linear Stack Alignment with SIFT", "initial_gaussian_blur=1.60 steps_per_scale_octave=3 minimum_image_size=64 maximum_image_size=1024 feature_descriptor_size=4 feature_descriptor_orientation_bins=8 closest/next_closest_ratio=0.92 maximal_alignment_error=25 inlier_ratio=0.05 expected_transformation=Rigid interpolate show_transformation_matrix")
		imp_align = wm.getImage("Aligned {} of {}".format(frame_no, frame_no))
		aligninfo = ParseTransformationMatrix()
		
		#!!!!!!!!!!!!!!!!! CLEAR LOG and get return
		IJ.log("\\Clear")
		return imp_align, aligninfo

def translate_stack (imp, aligninfo):
	
	channel_no, slice_no, frame_no = getShape(imp)
	print(channel_no, slice_no, frame_no)
	FileName = imp.getTitle()
	print("This is the filename of the one that will be translated {}".format(FileName))
	xAlign = 0
	yAlign = 0
	
	if slice_no>frame_no:
		rangestack = slice_no
	else:
		rangestack = frame_no
		
	for i in range(rangestack): #Change to frame_no
		#Will translate image based on alignment info
		
		xAlign = xAlign + aligninfo[i][0]
		yAlign = yAlign + aligninfo[i][1]
		print("Align info to change BF  {}, {}, on frame: {}".format(xAlign, yAlign, (i+1)))
		imp.setSlice(i+1)
		IJ.run(imp, "Translate...", "x={} y={} interpolation=None slice".format(xAlign, yAlign))
	
	"""
	else:
		xAlign = xAlign + aligninfo[0][0]
		yAlign = yAlign + aligninfo[0][1]
		print("Align info to change BF  {}, {}, on frame: {}".format(xAlign, yAlign, (0)))
		IJ.run(imp, "Translate...", "x={} y={} interpolation=None ".format(xAlign, yAlign))
	"""
	return imp

	
def getROIBF (imp, aligninfo, fldr_mask):
	#Making sure that all values are the values in pixel
	IJ.run("Set Scale...", "distance=0 known=1 unit=pixel")
	
	#Enhancing contrast of BF image
	IJ.run(imp, "8-bit", "stack")
	#IJ.run(imp, "Enhance Contrast...", "saturated=0.001 equalize process_all use")	
	#IJ.run(imp, "Gaussian Blur...", "sigma=2 stack")

	imp = translate_stack (imp, aligninfo)
	imp.show()
	
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
	#GET BIGGEST ROI OUT OF ARRAYS TO CALCULATE CENTROIDS
	print(ra)
	
	print(ra[0])
	
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
	impcrop = cropImage(imp, c_x, c_y)
		
	return c_x, c_y, roimask

def getROIpoints(imp, x, y, outputDir):
	FileName = imp.getTitle()

	#Creates a mask based on the ROI drawn for the area that you want to collect
	roim = RoiManager()
	rm = roim.getRoiManager()
	ra = rm.getRoisAsArray()
	imp.setRoi(ra[0])
	
	
	mask = imp.createRoiMask()
	maskImp = ImagePlus("Mask", mask)
	maskImp.show()
			
	IJ.run(maskImp, "Maximum...", "radius=75.5") #Adding 20 um of buffer space between colony outline and edge of mask (1.55 px/um for 10x TFM, change if using different magnification/microscope)

	IJ.run(maskImp, "Select None", "")
	maskImpCrop = cropImage(maskImp, x, y, FileName_OG = FileName)
	
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


def cropImage(imp, x, y, roi = 0, FileName_OG = "placeholder"):
	#Necessary to make a FileName_OG variable because stacked images after alignment lose their Filename, so in that case, a FileName is passed during the crop
	#This next FileName is the one that the passed imp has in the program (for BF images, it is the original FileName, for stacked/aligned, it will be different)
	FileName = imp.getTitle()
	
	#Making sure that no ROI is selected before crop
	IJ.run(imp, "Select None", "")
	print("For crop of file {}, center used is {}, {}".format(FileName, x,y))
	
	
	#Creating the shift for the beads unstressed image by adding the centroid of the BF to the alignment info of the stressed beads images
	#The "T" is specifically because triangle shaped colonies require a different aspect ratio for the crop
	if "-T" in FileName:
		y = y+280
		IJ.run(imp, "Specify...", "width={} height={} x={} y={} centered".format(1950, 1750, x, y))
	else:
		IJ.run(imp, "Specify...", "width={} height={} x={} y={} centered".format(1700, 1700, x, y))
		
	
	impcrop = IJ.run(imp, "Duplicate...", "duplicate title={}-crop".format(FileName))
	impcrop = wm.getImage("{}-crop".format(FileName))

	return impcrop


		
def PIV (imp, fldr, Name):
	print("Start PIV")
	
	
	PIVname=Name.replace(".tif","")
	#imp.changes = False
	print(fldr)
	fldr = fldr+"\\"
	
	IJ.run("iterative PIV(Advanced)...", "  piv1=128 sw1=256 vs1=64 piv2=64 sw2=128 vs2=32 piv3=48 sw3=128 vs3=16 correlation=0.60 batch postprocessing=DMT postprocessing_0=3 postprocessing_1=1 path={}".format(fldr))
	
	imp_piv1 = wm.getImage(Name+"_PIV1")
	imp_piv1.changes = False
	imp_piv1.close()
	imp_piv2 = wm.getImage(Name+"_PIV2")
	imp_piv2.changes = False
	imp_piv2.close()
	imp_piv3 = wm.getImage(Name+"_PIV3")
	imp_piv3.close()


def FTTC(pathin, pathout):
	print("Start FTTC at {}".format(pathin))

	gui = GenericDialog("FTTC")

	gui.addChoice("Magnification:",["10X objective + 1.0X relay", "10X objective + 1.5X relay", "20X objective + 1.0X relay", "20X objective + 1.5X relay"],"10X objective + 1.0X relay");
	gui.addNumericField("Young's modulus (Pascals):", 1500)
	gui.addNumericField("Regularization factor:", 0.00000000008, 13, 15, "(default is 0.00000000008)")
	gui.showDialog()

	if gui.wasOKed():
		mag = gui.getNextChoice();
		if (mag=="10X objective + 1.0X relay"): umpx=0.645
		if (mag=="10X objective + 1.5X relay"): umpx=0.430
		if (mag=="20X objective + 1.0X relay"): umpx=0.322
		if (mag=="20X objective + 1.5X relay"): umpx=0.215
		gelPa = gui.getNextNumber()
		reg = gui.getNextNumber()

	filesPIV = [x for d, dirs, files in os.walk(pathin) for x in files if "PIV3_DMT_disp" in x]
	print(filesPIV)

	pathPIV = [os.path.join(pathin, x) for x in filesPIV]
	print(pathPIV)
	
	for i in range(len(pathPIV)):
		FileName = filesPIV[i]
		
		FileName_base = (FileName.replace("PIV","")).replace(".txt","").replace(".tif","").replace("3_DMT_disp","").replace("Nadia_Weaver","").replace("Shaded", "")
		print("FTTC starting on file {} on {}".format(FileName_base, pathPIV[i]))

		t_string = ["T1", "T2", "T3", "T4"]
		if any(x in FileName_base for x in t_string):
			IJ.run("FTTC ", "pixel={} poisson=0.5 young's={} regularization={} plot plot_0=1900 plot_1=1900 select={}".format(umpx, gelPa, reg, pathPIV[i]))
		else:
			IJ.run("FTTC ", "pixel={} poisson=0.5 young's={} regularization={} plot plot_0=1700 plot_1=1700 select={}".format(umpx, gelPa, reg, pathPIV[i]))
				
		IJ.run("plot FTTC", "select=["+pathin+"\\Traction_"+FileName+"] autoscale vector_scale=1 max=500 plot_width=0 plot_height=0 show lut=S_Pet")
		
		imp_traction = wm.getImage("Traction Magnitude_"+FileName)
		imp_traction.close()

		imp_vectortraction = wm.getImage("Vector plot_Traction_"+FileName)
		IJ.saveAs(imp_vectortraction, "Tiff", pathout+"\\"+"Vector plot_Traction_"+FileName_base)	
		imp_vectortraction.close()

			
		impscale = wm.getImage("Scale Graph")
		
		IJ.saveAs(impscale, "Tiff", pathout+"\\"+"Traction-scale"+FileName_base)
		impscale.close()
		IJ.run("Close All")


def makepairs(fldr_pair, fldr_stacksBF, fldr_masks):
	#fldr_pair is the folder in which to save the pairs
	unstDir = IJ.getDirectory("1. Gimme the directory for the unstressed")
	print("Unst {}".format(unstDir))
	stDir = IJ.getDirectory("2. Gimme the directory for the stressed")
	print("Stressed directory {}".format(stDir))
	BFstDir = IJ.getDirectory("3. Gimme the directory of the channel to use as an outline to crop")
	print("Directory for outline {}".format(BFstDir))
	
	gui = GenericDialog("File Ordering")

	gui.addNumericField("Is there another channel to align? if so, add the number of remaining channels (0 if no)", 0)
	gui.showDialog()
	
	if gui.wasOKed():
		more_channels = gui.getNextNumber()
		if more_channels>0: 
			channel_listoflists = []
			for i in range(int(more_channels)):
				pathNext = []
				NextstDir = IJ.getDirectory("4. Gimme the directory of the next channel to align")
				pathNext = [os.path.join(d, x) for d, dirs, files in os.walk(NextstDir) for x in files if ".tif" in x]
				#Making sure that it is ordered alphabetically
				pathNext = sorted(pathNext)
				channel_listoflists.append(pathNext)
				print("There are {} files in the additional channel".format(len(channel_listoflists)))

	pathStress = [os.path.join(d, x) for d, dirs, files in os.walk(stDir) for x in files if ".tif" in x]
	#Making sure that it is ordered alphabetically
	pathStress = sorted(pathStress)
	
	pathUnstress = [os.path.join(d, x) for d, dirs, files in os.walk(unstDir) for x in files if ".tif" in x]
	#Making sure that it is ordered alphabetically
	pathUnstress = sorted(pathUnstress)

	pathBF = [os.path.join(d, x) for d, dirs, files in os.walk(BFstDir) for x in files if ".tif" in x]
	#Making sure that it is ordered alphabetically
	pathBF = sorted(pathBF)

	#Checking if there is the same number of files
	if len(pathStress) == len(pathUnstress):
		print("There is the same number of files for stress and unstressed")
		for i in range(0,len(pathStress)):
			
			#Opening Unstressed image of beads
			print("Opening Unstressed image {} in {}".format(i, pathUnstress[i]))
			impUnst = run(pathUnstress[i])
			FileNameUnst = impUnst.getTitle()
			#Opening Stressed image of beads
			print("Opening Stressed image {} in {}".format(i, pathStress[i]))
			impSt = run(pathStress[i])
			#Opening BF/other channel that will be used to create outline
			print("Opening BF image {} in {}".format(i, pathBF[i]))
			impBF = run(pathBF[i])
			
			FileNameSt = impSt.getTitle()
			FileNameUnst = impUnst.getTitle()
			FileNameBF = impBF.getTitle()

			if FileNameSt[0:3]== FileNameUnst[0:3]and FileNameSt[0:3] == FileNameBF[0:3]:
				print("Filenames are the same and we have BF images for every unstressed and stressed bead image")			
				print(FileNameSt)
				
				#Will concatenate unstressed image with stack of beads images
				impAll = Concatenator.run(impUnst, impSt)
				impAll.show()
				channel_no, slice_no, frame_no = getShape(impAll)
				print("Shape: Channels {}, Slices {}, Frame {}".format(channel_no, slice_no, frame_no))

				#Starting the alignment of the beads image
				imp_align, aligninfo = linearalignment(impAll, method = "SIFT")
				
				#Getting the outline to crop images
				impBF = wm.getImage(FileNameBF)
				c_x, c_y, roimask = getROIBF (impBF, aligninfo, fldr_masks)

				impBF.changes = False	
				impBF.close()
				#Saving cropped outline image
				FileNameBF_base = FileNameBF.replace(".tif","")
				path_pair_BFcrop = os.path.join(fldr_stacksBF, FileNameBF_base+"-crop")
				
				impBFcrop = wm.getImage(FileNameBF+"-crop")
				IJ.saveAs(impBFcrop, "Tiff",path_pair_BFcrop)
				
				#Now cropping the aligned beads image
				FileNameSt_base = FileNameSt.replace(".tif","")
				imp_align= wm.getImage("Aligned {} of {}".format(frame_no, frame_no))
				imp_align_crop = cropImage(imp_align, c_x, c_y, roimask, FileNameSt_base)
				imp_align_crop = wm.getImage("Aligned".format(frame_no, frame_no)) 
				
				#Creating individual files for each image so that substacks stay within the same spot
				fldr_pair_ind = os.path.join(fldr_pair, FileNameSt_base)
				mkdir_p(fldr_pair_ind)

				#Creating individual files for each timepoint
				fldr_stacksBF_ind = os.path.join(fldr_stacksBF, FileNameSt_base)
				mkdir_p(fldr_stacksBF_ind)

				#Aligning and cropping extra channels
				if more_channels:
					for j in range(int(more_channels)):
						pathChannel = channel_listoflists[j]
						imp_Channel = run(pathChannel[i])
						
						
						#IJ.run(imp_Channel, "Enhance Contrast...", "saturated=0.01 equalize process_all use")
						#Using Gaussian Blur to blur out background inconsistent signal
						IJ.run(imp_Channel, "8-bit", "stack")
						IJ.run(imp_Channel, "Gaussian Blur...", "sigma=2 stack")
						
						FileNameChannel = imp_Channel.getTitle()
						FileNameChannel_base = FileNameChannel.replace(".tif","")
						#Translating the alignment info into the additional channels
						imp_Channel_translated = translate_stack(imp_Channel, aligninfo)
						#Now cropping the additional channels
						imp_Channel_crop = cropImage(imp_Channel_translated, c_x, c_y, roimask, FileNameChannel_base)
						path_Channelcrop = os.path.join(fldr_stacksBF, FileNameChannel_base+"-crop")
						IJ.saveAs(imp_Channel_crop, "Tiff",path_Channelcrop)
						imp_Channel.changes = False
						imp_Channel.close()
						imp_Channel_translated.changes = False
						imp_Channel_translated.close()

				
				
				#In some datasets, time shows up as slice_no, others as frame_no. Assumes that bigger number is always time. Reevaluate if doing a short timelapse with multiple z slices
				if slice_no> frame_no:
					#Creates a substack with unstressed (first image) x stressed image over time
					#Also creates individiual files out of the slices in the other channels for later analysis
					for j in range(slice_no-1):
						print("Am I making a substack?")
	
						imp_BF_Sub = IJ.run(impBFcrop, "Make Substack...", "  slices={}".format(j+1))
						SubTitle_BF = ("Substack({})_{}".format(j+1, FileNameBF_base+"-crop"))
						path_ind_BF = os.path.join(fldr_stacksBF_ind, SubTitle_BF)
						
						IJ.saveAs(imp_BF_Sub, "Tiff",path_ind_BF) 		
						imp_BF_Sub = wm.getImage(SubTitle_BF+".tif")	
						imp_BF_Sub.close()

						if more_channels:
							for k in range(int(more_channels)):
								print("Am I making a substack of extra channels?")
		
								imp_Channel_crop_Sub = IJ.run(imp_Channel_crop, "Make Substack...", "  slices={}".format(j+1))
								SubTitle_Channel = ("Substack({})_{}".format(j+1, FileNameChannel_base+"-crop"))
								path_ind_Channel = os.path.join(fldr_stacksBF_ind, SubTitle_Channel)
							
								IJ.saveAs(imp_Channel_crop_Sub, "Tiff",path_ind_Channel) 		
								imp_Channel_crop_Sub = wm.getImage(SubTitle_Channel+".tif")
								imp_Channel_crop_Sub.close()
							
						
						
						path_pair_crop = os.path.join(fldr_stacksBF, FileNameSt)
						IJ.saveAs(imp_align_crop, "Tiff",path_pair_crop)
											
						imp_Sub = IJ.run(imp_align_crop, "Make Substack...", "  slices={},{}".format(1, j+2))
						SubTitle = ("Substack({})-({})_{}".format(1,j+2, FileNameSt))
							
						path_pair_sub = os.path.join(fldr_pair_ind, SubTitle)
						print("Yes, I did there {}".format(path_pair_sub))
						
						IJ.saveAs(imp_Sub, "Tiff",path_pair_sub) 
						
						imp_Sub = wm.getImage(SubTitle)
						imp_Sub.close()
					if more_channels:
						imp_Channel_crop = wm.getImage(FileNameChannel_base+"-crop.tif")
						imp_Channel_crop.close()
				if frame_no>slice_no:
					print(frame_no)
					for j in range(frame_no-1):
						print("Am I making a substack?")
	
						imp_BF_Sub = IJ.run(impBFcrop, "Make Substack...", "  slices={}".format(j+1))
						SubTitle_BF = ("Substack({})_{}".format(j+1, FileNameBF_base+"-crop"))
						path_ind_BF = os.path.join(fldr_stacksBF_ind, SubTitle_BF)
						
						IJ.saveAs(imp_BF_Sub, "Tiff",path_ind_BF) 		
						imp_BF_Sub = wm.getImage(SubTitle_BF+".tif")	
						imp_BF_Sub.close()

						if more_channels:
							for k in range(int(more_channels)):
								print("Am I making a substack of extra channels?")
		
								imp_Channel_crop_Sub = IJ.run(imp_Channel_crop, "Make Substack...", "  slices={}".format(j+1))
								SubTitle_Channel = ("Substack({})_{}".format(j+1, FileNameChannel_base+"-crop"))
								path_ind_Channel = os.path.join(fldr_stacksBF_ind, SubTitle_Channel)
							
								IJ.saveAs(imp_Channel_crop_Sub, "Tiff",path_ind_Channel) 		
								imp_Channel_crop_Sub = wm.getImage(SubTitle_Channel+".tif")
								imp_Channel_crop_Sub.close()
							
						
						
						path_pair_crop = os.path.join(fldr_stacksBF, FileNameSt)
						IJ.saveAs(imp_align_crop, "Tiff",path_pair_crop)
											
						imp_Sub = IJ.run(imp_align_crop, "Make Substack...", "  slices={},{}".format(1, j+2))
						SubTitle = ("Substack({})-({})_{}".format(1,j+2, FileNameSt))
							
						path_pair_sub = os.path.join(fldr_pair_ind, SubTitle)
						print("Yes, I did there {}".format(path_pair_sub))
						
						IJ.saveAs(imp_Sub, "Tiff",path_pair_sub) 
						
						imp_Sub = wm.getImage(SubTitle)
						imp_Sub.close()
					if more_channels:
						imp_Channel_crop = wm.getImage(FileNameChannel_base+"-crop.tif")
						imp_Channel_crop.close()

				
				impBFcrop = wm.getImage(FileNameBF_base+"-crop.tif")
				impBFcrop.close()
				
				#Closing the concatenated image
				impAll = wm.getImage("Untitled")
				impAll.changes = False	
				impAll.close()
		
				#Closing the aligned beads image
				imp_align = wm.getImage("Aligned {} of {}".format(frame_no, frame_no))
				imp_align.close()
				
				#Closing the cropped aligned beads image
				imp_align_crop = wm.getImage(FileNameSt)
				imp_align_crop.changes = False	
				imp_align_crop.close()
			else:
				print("Filenumber for unstressed and stressed is not the same. Aborting.")	

				
def makepairs_fromaligned_sequential(fldr_pairs, fldr_stacks):
	#This function is for creating sequential pairs for PIV instead of unstressed x stressed
	
	#Trying to get aligned and cropped stack
	pathStack = [os.path.join(d, x) for d, dirs, files in os.walk(fldr_stacks) for x in files if "Ch0" in x and "Substack" not in x]
	#Making sure that it is ordered alphabetically
	pathStack = sorted(pathStack)

	for i in range(len(pathStack)):
		#Opening aligned and cropped Stack
		print("Opening Aligned and cropped stack {} in {}".format(i, pathStack[i]))
		impStack = run(pathStack[i])
		FileNameStack = impStack.getTitle()
		FileNameStack_base = FileNameStack.replace(".tif", "")

		impStack.show()
		channel_no, slice_no, frame_no = getShape(impStack)
		print("Shape: Channels {}, Slices {}, Frame {}".format(channel_no, slice_no, frame_no))


		fldr_pair_ind = os.path.join(fldr_pairs, FileNameStack_base+"_Seq")
		mkdir_p(fldr_pair_ind)
		
		if frame_no>slice_no:
			range_stack = frame_no
		else:
			range_stack = slice_no
		for j in range(range_stack-1):
			print("Am I making a substack?")

											
			imp_Sub_Seq = IJ.run(impStack, "Make Substack...", "  slices={},{}".format(j+1, j+2))
			SubTitle = ("Substack-Seq_({})-({})_{}".format(j+1,j+2, FileNameStack))
				
			path_pair_sub = os.path.join(fldr_pair_ind, SubTitle)
			print("Yes, I did there {}".format(path_pair_sub))
			
			IJ.saveAs(imp_Sub_Seq, "Tiff",path_pair_sub) 

			imp_Sub_Seq = wm.getImage(SubTitle)		
			imp_Sub_Seq.close()
		impStack.close()
			



def function (srcDir):
	"""
	Will create folders if not existent for manipulations
	Then will create pairs of unstressed and stressed bead images
	Will do PIV and FTTC sequentially
	If FTTC fails, delete all FTTC_Parameters files from PIV before commenting out makepairs and PIV from this function and running again
	
	"""
		
	#Create Directory for pairs, PIV and FTTC outputs
	fldr_pair = os.path.join(srcDir, "4_TF-Pairs")
	mkdir_p(fldr_pair)
	fldr_stacksBF = os.path.join(srcDir, "5_Stacks_BF-edited")
	mkdir_p(fldr_stacksBF)
	fldr_masks = os.path.join(srcDir, "6_Masks")
	mkdir_p(fldr_masks)
	fldr_PIV = os.path.join(srcDir, "7_PIV")
	mkdir_p(fldr_PIV)
	fldr_FTTC = os.path.join(srcDir, "8_FTTC")
	mkdir_p(fldr_FTTC)
	
	
	makepairs(fldr_pair, fldr_stacksBF, fldr_masks)
	
	pathPair = [os.path.join(d, x) for d, dirs, files in os.walk(fldr_pair) for x in files if "Substack(" in x]
	print(pathPair)
	for i in range(len(pathPair)):
		print("Opening pair image {} in {}".format(i, pathPair[i]))
		imp = run(pathPair[i])
		FileName = imp.getTitle()
		PIV(imp, fldr_PIV, FileName)
		imp.changes = False
		imp.close()
	
	FTTC(fldr_PIV, fldr_FTTC)
	"""
	#Now to do sequential pairs and do the PIV and FTTC on them:
	makepairs_fromaligned_sequential(fldr_pair, fldr_stacksBF)
	pathPairSeq = [os.path.join(d, x) for d, dirs, files in os.walk(fldr_pair) for x in files if "Substack-Seq_" in x]
	fldr_PIV_Seq = os.path.join(srcDir, "7_PIV_Seq")
	mkdir_p(fldr_PIV_Seq)
	fldr_FTTC_Seq = os.path.join(srcDir, "8_FTTC_Seq")
	mkdir_p(fldr_FTTC_Seq)
	
	for j in range(len(pathPairSeq)):
		print("Opening pair image {} in {}".format(j, pathPairSeq[j]))
		imp = run(pathPairSeq[j])
		FileName = imp.getTitle()
		PIV(imp, fldr_PIV_Seq, FileName)
		imp.changes = False
		imp.close()

	FTTC(fldr_PIV_Seq, fldr_FTTC_Seq)
	"""	
	print("Done :D")
	
#Set input directory and RUN PROGRAM...
srcDir = IJ.getDirectory("Source Images for reference")
print "Source directory: ", srcDir
function(srcDir)


