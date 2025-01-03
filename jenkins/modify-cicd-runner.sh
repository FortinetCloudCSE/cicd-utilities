#!/bin/bash
# Script for modifying a list of existing GitHub repos configurations and/or creating a pipeline in Jenkins for an existing GitHub repo.
# execute modify-cicd.sh on all repos listed in <strings.txt> file (one repo name per line with a blank line at the end)
#
# Usage:
# ./modify-cicd-runner.sh  <strings.txt> [-j userid] [-c username -c username ... ] [-w] [-r] [-b] [-a] [-f template-config.xml]
#   -j Jenkins userid; if left out only GitHub operations will be performed
#   -c usernames of collaborator to add to repo
#   -w add a Jenkins webhook to the repo
#   -r remove Main branch protections
#   -u update README with GitHub pages URL
#   -b add branch protections based on Jenkins pipeline execution status
#   -f specify a Jenkins pipeline configuration xml
#   -a Trigger Fortinet CloudCSE github action (rebuild with latest CentralRepo Container)

# Check if at least 2 arguments are passed (input file and other args for modify-cicd.sh)
if [ $# -lt 2 ]; then
    echo "Usage: $0 <input_file> [additional_arguments_for_modify_cicd]"
    exit 1
fi

# Extract the first argument as the input file
input_file=$1

# Remove the first argument (input file) and pass the remaining as additional arguments
shift

echo "Reading input file: $input_file"
echo "Additional arguments: $@"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Input file $input_file does not exist"
    exit 1
fi

# Read the file and loop over each line
while IFS= read -r stringname; do
    # Check if the string is not empty
    if [ -n "$stringname" ]; then
        echo "Executing: ./modify-cicd.sh -f \"$stringname\" $@"
        # Run the modify-cicd.sh script with the string and additional arguments
        ./modify-cicd.sh "$@" "$stringname"
    fi
done < "$input_file"