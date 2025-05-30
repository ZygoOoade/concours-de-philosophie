# -*- coding: utf-8 -*-

Original file is located at
    https://colab.research.google.com/drive/1uKzMt4JQimPgHW3U9K9d8XWiqLAEI3CH
"""

import shutil
import os

src = '/content/drive/MyDrive/Le vrai et le réel (AGREG 2020 - note : 13,5)'
dst = '/content/model'

if os.path.exists(dst):
    shutil.rmtree(dst)

shutil.copytree(src, dst)

import shutil
import os

src = '/content/drive/MyDrive/main'
dst = '/content/to_crop'

if os.path.exists(dst):
    shutil.rmtree(dst)

shutil.copytree(src, dst)

#@title Découpage du header grâce à un modèle

import os
from PIL import Image
import sys # For potentially exiting on critical errors
import re # Import regular expressions module

print("--- Image Cropping Script Started (v3 - Handling Number Padding) ---")

# --- Configuration ---
model_folder = "/content/model"
to_crop_base_folder = "/content/to_crop"
# --- End Configuration ---

# --- Helper Function to Extract Page Number ---
def extract_page_number(filename):
    """
    Extracts the integer page number from filenames like:
    page_001.png, Page_1.PNG, document_05.png etc.
    Returns the integer number or None if no number is found.
    """
    # Regex to find one or more digits (\d+) potentially preceded by common separators (_ or - or space)
    # It looks for digits occurring before the .png extension (case-insensitive)
    match = re.search(r'[_ \-]?(?P<number>\d+)\.(png|jpeg|jpg|tif|tiff)$', filename, re.IGNORECASE)
    if match:
        try:
            return int(match.group('number'))
        except (ValueError, TypeError):
            return None # Should not happen with \d+ but good practice
    else:
        # Fallback: Maybe just digits before extension?
        match = re.search(r'(?P<number>\d+)\.(png|jpeg|jpg|tif|tiff)$', filename, re.IGNORECASE)
        if match:
            try:
                return int(match.group('number'))
            except (ValueError, TypeError):
                return None
    print(f"    Debug: Could not extract page number from filename: '{filename}'")
    return None # No number found

# --- Input Validation ---
if not os.path.isdir(model_folder):
    print(f"Error: Template folder not found: {model_folder}")
    sys.exit(1)

if not os.path.isdir(to_crop_base_folder):
    print(f"Error: Base folder to crop not found: {to_crop_base_folder}")
    sys.exit(1)

# --- Step 1: Determine Crop Thresholds using Page Numbers ---
print(f"\n--- Step 1: Determining Crop Thresholds from '{model_folder}' (Matching by Page Number) ---")
# Store thresholds keyed by page number (integer) instead of filename string
crop_thresholds_by_num = {} # Dictionary: { 1: y_threshold, 2: y_threshold, ... }

# List PNG files in the model folder
try:
    model_filenames = [f for f in os.listdir(model_folder) if re.search(r'\.(png|jpeg|jpg|tif|tiff)$', f, re.IGNORECASE)]
    if not model_filenames:
         print(f"Warning: No image files (png, jpg, etc.) found in the template folder: {model_folder}")
except OSError as e:
     print(f"Error listing files in template folder {model_folder}: {e}")
     sys.exit(1)

# Find subfolders to sample original heights
try:
    subfolders = [os.path.join(to_crop_base_folder, d) for d in os.listdir(to_crop_base_folder) if os.path.isdir(os.path.join(to_crop_base_folder, d))]
    if not subfolders and model_filenames:
         print(f"Warning: No subfolders found within '{to_crop_base_folder}'. Cannot determine original heights.")
except OSError as e:
     print(f"Error listing subfolders in {to_crop_base_folder}: {e}")
     sys.exit(1)

# Iterate through each template file
for template_filename in sorted(model_filenames): # Sort for consistent processing if needed
    template_path = os.path.join(model_folder, template_filename)
    template_page_num = extract_page_number(template_filename)

    if template_page_num is None:
        print(f"  Warning: Could not extract page number from template '{template_filename}'. Skipping.")
        continue

    # Avoid recalculating if already found for this page number (e.g., if multiple templates exist for same page)
    if template_page_num in crop_thresholds_by_num:
        continue

    original_height = None
    template_height = None
    original_image_path_found = None

    try:
        # Get template height
        with Image.open(template_path) as model_img:
            template_height = model_img.height

        # Find *one* corresponding image in any subfolder based on PAGE NUMBER
        if subfolders:
            found_match_in_subfolders = False
            for subfolder in subfolders:
                try:
                    for target_filename in os.listdir(subfolder):
                         target_path = os.path.join(subfolder, target_filename)
                         if os.path.isfile(target_path): # Ensure it's a file
                            target_page_num = extract_page_number(target_filename)
                            # Check if the extracted number matches the template's number
                            if target_page_num == template_page_num:
                                try:
                                    with Image.open(target_path) as uncropped_img:
                                        original_height = uncropped_img.height
                                        original_image_path_found = target_path
                                        found_match_in_subfolders = True
                                        # print(f"    Debug: Found match for page {template_page_num}: '{target_path}' (H={original_height})")
                                        break # Found representative original for this page number
                                except Exception as img_err:
                                     print(f"  Warning: Could not open sample image '{target_path}' to determine height for page {template_page_num}. Error: {img_err}")
                                     # Continue searching in the same subfolder or next one
                    if found_match_in_subfolders:
                         break # Stop searching subfolders once a match is found and opened
                except OSError as list_err:
                     print(f"  Warning: Could not list files in subfolder '{subfolder}'. Skipping it for threshold calculation. Error: {list_err}")
            # Check if we found a sample after searching all subfolders
            if not found_match_in_subfolders:
                 print(f"  Warning: Could not find any corresponding image for page number {template_page_num} (from '{template_filename}') in subfolders of '{to_crop_base_folder}'. Cannot determine threshold.")


        # Calculate and store the threshold if heights were found
        if template_height is not None and original_height is not None:
            y_threshold = original_height - template_height
            if y_threshold < 0:
                 print(f"  Warning: Calculated negative threshold ({y_threshold}) for page {template_page_num} ('{template_filename}'). "
                       f"Original height ({original_height} from {original_image_path_found}) might be smaller than template height ({template_height}). "
                       f"Setting threshold to 0.")
                 y_threshold = 0

            crop_thresholds_by_num[template_page_num] = y_threshold
            print(f"  Threshold for Page {template_page_num}: Remove y={y_threshold} pixels from top (Based on Original H: {original_height}, Template H: {template_height})")

        elif template_height is None:
             print(f"  Error: Could not read template image '{template_path}'. Skipping threshold calculation.")
        # No 'else' needed, warning about not finding match covers other cases

    except FileNotFoundError:
        print(f"  Error: Template file not found '{template_path}'. Skipping.")
    except Exception as e:
        print(f"  Error processing template '{template_path}': {e}. Skipping threshold calculation.")

if not crop_thresholds_by_num:
     print("\nWarning: No crop thresholds were determined. No images will be cropped.")

# --- Step 2: Apply Cropping using Page Numbers ---
print(f"\n--- Step 2: Applying Cropping to Images in '{to_crop_base_folder}' Subfolders (Matching by Page Number) ---")

processed_count = 0
skipped_count = 0
error_count = 0

# Iterate through each subfolder
for subfolder_name in os.listdir(to_crop_base_folder):
    subfolder_path = os.path.join(to_crop_base_folder, subfolder_name)

    if os.path.isdir(subfolder_path):
        print(f"\nProcessing folder: '{subfolder_path}'")
        try:
            # Iterate through each file in the current subfolder
            for filename in sorted(os.listdir(subfolder_path)): # Sort for predictable order
                target_image_path = os.path.join(subfolder_path, filename)
                if not os.path.isfile(target_image_path): # Skip directories
                    continue

                # Extract page number from the target filename
                target_page_num = extract_page_number(filename)

                if target_page_num is not None:
                    # Check if we have a calculated threshold for this PAGE NUMBER
                    if target_page_num in crop_thresholds_by_num:
                        calculated_y_threshold = crop_thresholds_by_num[target_page_num]
                        current_y_to_crop = calculated_y_threshold

                        try:
                            with Image.open(target_image_path) as img:
                                width, height = img.size

                                # Safety Check against image height
                                if calculated_y_threshold >= height:
                                     print(f"  Warning: Calculated header height ({calculated_y_threshold}px) for page {target_page_num} is >= actual image height ({height}px) for '{filename}'. Setting crop amount to 0.")
                                     current_y_to_crop = 0
                                elif calculated_y_threshold < 0:
                                      print(f"  Warning: Negative crop threshold ({calculated_y_threshold}) encountered for page {target_page_num} ('{filename}'). Setting crop amount to 0.")
                                      current_y_to_crop = 0

                                # Define crop box
                                crop_box = (0, current_y_to_crop, width, height)

                                # Perform crop only if necessary and valid
                                if current_y_to_crop >= height:
                                     print(f"  Skipping crop for '{filename}' as adjusted crop area is invalid (Crop top {current_y_to_crop} >= Height {height}).")
                                     skipped_count +=1
                                elif current_y_to_crop <= 0:
                                     # Log skipping if threshold was 0 or adjusted to 0
                                     reason = "calculated threshold was 0" if calculated_y_threshold <= 0 else "height constraint"
                                     print(f"  Skipping crop for '{filename}' as {reason}. Image not modified.")
                                     skipped_count += 1
                                else:
                                    # Proceed with cropping
                                    cropped_img = img.crop(crop_box)
                                    save_kwargs = {}
                                    if 'icc_profile' in img.info: save_kwargs['icc_profile'] = img.info['icc_profile']
                                    if 'dpi' in img.info: save_kwargs['dpi'] = img.info['dpi']
                                    cropped_img.save(target_image_path, **save_kwargs)
                                    print(f"  Cropped and overwritten: '{filename}' (Removed {current_y_to_crop}px from top)")
                                    processed_count += 1

                        except FileNotFoundError:
                            print(f"  Error: Image file not found during processing: '{target_image_path}'. Skipping.")
                            error_count += 1
                        except Exception as e:
                            print(f"  Error processing image '{target_image_path}': {e}. Skipping.")
                            error_count += 1
                    else:
                        # Page number extracted, but no threshold was calculated for it (e.g., template missing)
                        print(f"  Skipping: '{filename}' (No threshold found for page number {target_page_num})")
                        skipped_count += 1
                else:
                    # Could not extract a page number from this filename
                    print(f"  Skipping: '{filename}' (Could not determine page number)")
                    skipped_count += 1
        except OSError as e:
             print(f"Error accessing files within subfolder '{subfolder_path}': {e}. Skipping this folder.")

print("\n--- Cropping Script Finished ---")
print(f"Summary:")
print(f"  Successfully cropped and overwritten: {processed_count} images")
print(f"  Skipped (no threshold, height constraint, 0 threshold, or unparsable): {skipped_count} images")
print(f"  Errors encountered during processing: {error_count} images/folders")
print("----------------------------------")

import os
import numpy as np
from PIL import Image, ImageStat
import ipywidgets as widgets
from IPython.display import display, clear_output, Image as IPImage
import io
import time # To prevent potential race conditions with display updates

# --- Configuration ---
MAIN_FOLDER_PATH = "/content/to_crop"  # <<< CHANGE THIS if your main folder is elsewhere
CONTRAST_THRESHOLD = 25.0  # <<< ADJUST AS NEEDED (lower = closer to pure white/black)
DISPLAY_WIDTH = 600 # Max width to display the image in pixels

# --- Globals for Interaction State ---
candidate_images = []
current_index = -1
output_area = widgets.Output() # Area to display images and buttons

# --- Helper Functions ---

def calculate_contrast(image_path):
    """
    Calculates a contrast metric for an image.
    Uses standard deviation of grayscale pixel values.
    Returns None if the file is not a valid image.
    """
    try:
        with Image.open(image_path) as img:
            # Convert to grayscale for simpler analysis
            grayscale_img = img.convert('L')
            # Calculate standard deviation of pixel values
            stat = ImageStat.Stat(grayscale_img)
            return stat.stddev[0] # stddev is a list with one element for grayscale
    except Exception as e:
        print(f"Error processing {image_path}: {e}")
        return None

def find_low_contrast_images(root_folder, threshold):
    """
    Scans the folder structure and finds images below the contrast threshold.
    """
    low_contrast_files = []
    print(f"Scanning folder: {root_folder} ...")
    if not os.path.isdir(root_folder):
        print(f"Error: Folder not found: {root_folder}")
        return []

    for subdir, _, files in os.walk(root_folder):
        # Sort files to process pages in order (e.g., Page_001, Page_002)
        # This helps if you want to stop early but keep pages sequential
        files.sort()
        for filename in files:
            if filename.lower().endswith('.png'):
                image_path = os.path.join(subdir, filename)
                contrast = calculate_contrast(image_path)
                if contrast is not None and contrast < threshold:
                    low_contrast_files.append(image_path)
                    print(f"  - Flagged: {os.path.relpath(image_path, root_folder)} (Contrast: {contrast:.2f})")

    print(f"\nFound {len(low_contrast_files)} potential blank pages to review.")
    return low_contrast_files

# --- Button Click Handlers ---

def on_keep_clicked(b):
    """Handles the Keep button click."""
    global current_index
    image_path = candidate_images[current_index]
    with output_area:
        clear_output(wait=True)
        print(f"Keeping: {os.path.relpath(image_path, MAIN_FOLDER_PATH)}")
        # Add a small delay to ensure the message is seen before the next image
        time.sleep(0.5)
        show_next_image()

def on_delete_clicked(b):
    """Handles the Delete button click."""
    global current_index
    image_path = candidate_images[current_index]
    try:
        os.remove(image_path)
        with output_area:
            clear_output(wait=True)
            print(f"Deleted: {os.path.relpath(image_path, MAIN_FOLDER_PATH)}")
            # Add a small delay
            time.sleep(0.5)
            show_next_image()
    except Exception as e:
         with output_area:
            clear_output(wait=True)
            print(f"Error deleting {os.path.relpath(image_path, MAIN_FOLDER_PATH)}: {e}")
            # Add a small delay
            time.sleep(1.0)
            # Still proceed to the next image even if deletion failed
            show_next_image()


# --- Display Logic ---

def show_next_image():
    """Displays the next candidate image or finishes."""
    global current_index
    current_index += 1

    with output_area: # Ensure output happens within the designated area
        if current_index < len(candidate_images):
            image_path = candidate_images[current_index]
            print(f"\nReviewing image {current_index + 1}/{len(candidate_images)}:")
            print(f"File: {os.path.relpath(image_path, MAIN_FOLDER_PATH)}")

            # Display Image using IPython.display.Image for better handling
            try:
                display(IPImage(filename=image_path, width=DISPLAY_WIDTH))
            except Exception as e:
                print(f"Error displaying image {image_path}: {e}")


            # Create Buttons
            keep_button = widgets.Button(description="Keep", button_style="success", icon="check")
            delete_button = widgets.Button(description="Delete", button_style="danger", icon="trash")

            # Assign click handlers
            keep_button.on_click(on_keep_clicked)
            delete_button.on_click(on_delete_clicked)

            # Display Buttons horizontally
            buttons = widgets.HBox([keep_button, delete_button])
            display(buttons)

        else:
            print("\n--- Review Complete ---")
            if len(candidate_images) == 0:
                print("No low-contrast images were found to review.")
            else:
                 print(f"Finished reviewing {len(candidate_images)} images.")


# --- Main Execution ---

# 1. Find candidates first
candidate_images = find_low_contrast_images(MAIN_FOLDER_PATH, CONTRAST_THRESHOLD)

# 2. Setup the display area and start the interactive review
display(output_area) # Display the output area widget FIRST
show_next_image() # Start the review process by showing the first image (if any)
