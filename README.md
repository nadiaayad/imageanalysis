# imageanalysis
This is a repository created by Nadia Ayad for image processing and analysis of fluorescence images and traction force microscopy for data in the paper:
"Tissue tension permits β-catenin phosphorylation to drive mesoderm specification in human embryonic stem cells" by Ayad et al.

Most scripts are used directly on Fiji. Script 6 runs on Jupyter.

The first code used is the TFM-FileOrdering-Python:
- It will separate .nd2 images per channel and create a folder depending on the amount of channels
- It will also create a new folder with a background correction (Pseudo Flat Field correction and Subtract Background)

The second code (Center_Crop), takes colonies images, prompts the user to outline it, then finds the centroid and crops the image around the colony to reduce image size.

The third script (ThrNuclei_inStarDistMask) is a javascript Fiji script to Threshold images and compare to a thresholded masks using a StarDist algorithm (needs to have it preinstalled in Fiji). User can comment out and change whether to use normal thresholding (and which algorithm) or StarDist for nuclear images. 

The fourth script (TFM_timelapse.py) will create traction force maps out of bead images, using another channel as an outline and mask.

The scripts 5 and 6 are to be used together, sequentially. They were used to generate Fig S4E, related to Fig4D.
Script 5 is used on Fiji to generates a structured csv file containing slice indices, ROI indices, and the mean intensities for designated target channels.
Script 6, on Jupyter, takes that .csv file and generates scatter plots with a regression line to analyze if channels are correlated.


