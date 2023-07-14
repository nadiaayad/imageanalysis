//=====NUCLEI QUANTIFICATION ANALYSIS v2===== 
//Written 2023-04-01 by Nadia Ayad, adapted by pSFK quant macro by Jon Muncie
// This macro automates quanTIFying thresholded areas of images based on a nuclear mask using StarDist
// This is version 1 of this macro 

//-----IMPORTANT NOTES-----
// In the root folder for the sample to be analyzed, user needs to create three (3) folders and name them after the directories below.
// Mask folder is the folder that will be used as a mask for later analysis (i.e. DAPI for nuclear stain)
// Measure folder is the folder with images that will be measured against the mask (i.e. is bCat nuclear based on the DAPI stain)

//-----MACRO-----
//ImageJ --headless -macro path-to-Macro.ijm
//close all open images, clear results, and clear log


close("*");
run("Clear Results");
print("\\Clear");

// Macro prompts to create input/output directories.
waitForUser("WAITING...", "Create the following directories:\n1.mask folder\n2.measure\n3.output");
// Macro prompts use to choose the input/output directories.
dir1 = getDirectory("Choose 'Mask' folder");
dir2 = getDirectory("Choose 'Measure' folder");
dir3 = getDirectory("Choose Output Directory");


print("Input1 - Mask images pulled from: "+dir1);
print ("Input2 - Images that will be masked pulled from: "+dir2);
print("Output Results To: "+dir3);

list1 = getFileList(dir1);
list2 = getFileList(dir2);
Array.sort(list1);
images1 = list1.length;
Array.sort(list2);
images2 = list2.length;

string1 = getString("What's the string name for first folder that will be used as a mask?","dapi");
print("Files from "+dir1+"will have the string "+string1);

string2 = getString("What's the string name for second folder that will be measured with a mask?","pSmad");
print("Files from "+dir2+"will have the string "+string2);



if (images1 == images2){
	print("Total number of ROIs to mask: "+ images1+" is the same number of ROIs to measure: " + images2 );
	
	for (i=0; i<list1.length; i=i+1){
		
		open(dir1+list1[i]);
		FileName1=list1[i];
		print("\nStarting threshold on file "+i+" named: "+FileName1+"\nand file has "+nSlices+" slices");
		run("8-bit");
		run("Measure");
		//For nuclear mask - comment out below:
		//run("Command From Macro", "command=[de.csbdresden.stardist.StarDist2D], args=['input':'"+FileName1+"', 'modelChoice':'Versatile (fluorescent nuclei)', 'normalizeInput':'true', 'percentileBottom':'1.0', 'percentileTop':'99.8', 'probThresh':'0.5', 'nmsThresh':'0.4', 'outputType':'Both', 'nTiles':'1', 'excludeBoundary':'2', 'roiPosition':'Automatic', 'verbose':'false', 'showCsbdeepProgress':'false', 'showProbAndDist':'false'], process=[false]");
		//selectWindow("Label Image");
		
		//run("Threshold...");
		//setThreshold(0, 1, "raw");
		//run("Convert to Mask");
		//run("Invert", "stack");
		//print("Threshold of mask: StarDist");
		
		//Thresholding mask normal way
	
		//run("Gaussian Blur...", "sigma=2 stack"); //Comment out if not nuclear sigma 5 for 60x 2 for 10x
		//thr1 = "Otsu"; // Select another auto threshold if it works better for this set of images
		//run("Auto Threshold", "method="+thr1+" white stack");
		//run("Invert", "stack");
		//print("Threshold mask: "+thr1);
						
		saveAs("Tiff", dir3 + replace(FileName1,".tif", "_1"+string1+"_mask"));
		run("Divide...", "value=255 stack");
		
		
		for (j=1; j<nSlices+1;j++) {
			setSlice(j); 	
			//Stack.getPosition(channel, slice, frame);
			//print("Slice number = "+slice); //Just to check the slice number
			run("Set Measurements...", "area mean integrated median display redirect=None decimal=3");
			//run("Measure");
		}
		open(dir2+list2[i]);
		FileName2=list2[i];
		print("Masking the raw file: "+FileName2+"\nand file has "+nSlices+" slices");
		run("Measure");
		//Thresholding Measured channel normal way - comment out if doing normal threshold
		//for the cleavcasp3
		//run("Subtract Background...", "rolling=50");
		//run("Gaussian Blur...", "sigma=2 stack"); //Comment out if not nuclear sigma 5 for 60x 2 for 10x
		//run("Brightness/Contrast...");
		//run("Enhance Contrast", "saturated=0.35");
		//run("Apply LUT");
		
		//thr2 = "Moments"; // Select another auto threshold if it works better for this set of images
		//run("Auto Threshold", "method="+thr2+" white stack");
		//print("Threshold measured: "+thr2);
		
		run("8-bit");
		run("Gaussian Blur...", "sigma=2 stack"); //Comment out if not nuclear sigma 5 for 60x 2 for 10x
		thr2 = "Moments"; // Select another auto threshold if it works better for this set of images
		run("Auto Threshold", "method="+thr2+" white stack");
		run("Invert", "stack");
		print("Threshold mask: "+thr2);
		
		
		//Thresholding nuclear measuring channel
		//run("Command From Macro", "command=[de.csbdresden.stardist.StarDist2D], args=['input':'"+FileName2+"', 'modelChoice':'Versatile (fluorescent nuclei)', 'normalizeInput':'true', 'percentileBottom':'1.0', 'percentileTop':'99.8', 'probThresh':'0.5', 'nmsThresh':'0.4', 'outputType':'Both', 'nTiles':'1', 'excludeBoundary':'2', 'roiPosition':'Automatic', 'verbose':'false', 'showCsbdeepProgress':'false', 'showProbAndDist':'false'], process=[false]");
		//selectWindow("Label Image");
		//run("8-bit");
		//run("Threshold...");
		//setThreshold(0, 1, "raw");
		//run("Convert to Mask");
		//run("Invert", "stack");
		//print("Threshold measured: StarDist");
		
		
		saveAs("Tiff", dir3 + replace(FileName2,".tif", "_2"+string2+"_thr"));
		run("Divide...", "value=255 stack");
		
		
		for (j=1; j<nSlices+1;j++) {
			setSlice(j); 
			run("Set Measurements...", "area mean integrated median display redirect=None decimal=3");
			run("Measure");
		}
		
		imageCalculator("Multiply create stack", replace(FileName1,".tif", "_1"+string1+"_mask.tif"), replace(FileName2,".tif", "_2"+string2+"_thr.tif"));	
		run("Multiply...", "value=255 stack");
		saveAs("Tiff", dir3 + replace(FileName2,".tif", "_3"+string2+"_masked"));
		run("Divide...", "value=255 stack");
		for (j=1; j<nSlices+1;j++) {
			setSlice(j); 	
			run("Set Measurements...", "area mean integrated median display redirect=None decimal=3");
			run("Measure");
		}
		
		print("Masked and saved the file: "+FileName2);
		
	
	close("*");	
}



//Macro saves Results window and log
selectWindow("Results");
saveAs("Text", dir3 + "Results_"+string2+"_quant_"+string1+"_mask");
print("ANALYSIS COMPLETE AND RESULTS SAVED");
selectWindow("Log");
saveAs("Text", dir3 + "Log_"+string2+"_quant_"+string1+"_mask");
print("LOG SAVED");