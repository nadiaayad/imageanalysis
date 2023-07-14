# imageanalysis
This is a repository created by Nadia Ayad for image processing and analysis of fluorescence images and traction force microscopy
Currently, it has one main project as a branch:
- Y654F mutant

The 3 first scripts are to be used directly on Fiji.

The first code used is the TFM-FileOrdering-Python:
- It will separate .nd2 images per channel and create a folder depending on the amount of channels
- It will also create a new folder with a background correction (Pseudo Flat Field correction and Subtract Background)

The second code (Center_Crop), takes colonies images, prompts the user to outline it, then finds the centroid and crops the image around the colony to reduce image size

The third script (ThrNuclei_inStarDistMask) is a javascript Fiji script to Threshold images and compare to a thresholded masks using a StarDist algorithm (needs to have it preinstalled in Fiji). User can comment out and change whether to use normal thresholding (and which algorithm) or StarDist for nuclear images. 

The fourth script will create traction force maps out of bead images, using another channel as an outline and mask.
