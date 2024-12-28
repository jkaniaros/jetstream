import re
import os

def merge_files_by_regex(in_folder: str, out_folder: str, regex: str, archive_folder: str):
    """
    Function to merge files specified by regex in a given folder into a given output folder.
    Checks for an archive file and only merges lines not already in the archive.

    Parameters:
    in_folder (str): The folder where the single files are stored.
    out_folder (str): The folder where the merged file should be saved.
    regex (str): The regex string for the files to be merged.
    archive_folder (str): The folder where archive files are stored.
    """

    # If the input folder does not exist, return
    if not os.path.exists(in_folder):
        return

    # Create output and archive folders if they don't exist
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    if not os.path.exists(archive_folder):
        os.makedirs(archive_folder)

    # Compile the regex pattern
    pattern = re.compile(regex)

    # Group files by regex match
    grouped_files = {}
    for file in os.listdir(in_folder):
        if os.path.isfile(os.path.join(in_folder, file)):
            match = pattern.search(file)
            if match:
                group_key = match.group(1).lstrip("0") # Use the station id in the filename as group key
                if group_key not in grouped_files:
                    grouped_files[group_key] = []
                grouped_files[group_key].append(file)

    # Merge files for each group
    for group_key, files in grouped_files.items():
        merge_file_path = os.path.join(out_folder, f"merged_{group_key}.txt")
        archive_file_path = os.path.join(archive_folder, f"archived_{group_key}.txt")

        # Read existing lines from the merge file if it exists
        existing_lines = set()
        if os.path.exists(merge_file_path):
            with open(merge_file_path, "r", encoding="UTF-8") as merge_file:
                existing_lines.update(line.strip() for line in merge_file)

        # Read existing lines from the archive file if it exists
        if os.path.exists(archive_file_path):
            with open(archive_file_path, "r", encoding="UTF-8") as archive_file:
                existing_lines.update(line.strip() for line in archive_file)

        # Append the non-existing and not already sent lines to the merge file
        with open(merge_file_path, "a", encoding="UTF-8") as merge_file:
            for file in files:
                file_path = os.path.join(in_folder, file)
                with open(file_path, "r", encoding="UTF-8") as in_file:
                    lines = in_file.readlines()
                    # Check if the first line contains header information. If yes, exclude it
                    if lines and lines[0].upper().startswith("STATION"):
                        lines = lines[1:]

                    for line in lines:
                        line = line.strip()
                        # Add line only if it's not already in the existing_lines
                        if line not in existing_lines:
                            merge_file.write(f"{line}\n")
                            existing_lines.add(line)  # Add to the set of existing lines

        print(f"Merged {len(files)} files into {merge_file_path}")
