echo "starting for loop"

original_ifs="$IFS"

IFS=$'\n'

changed_files=$(git diff --name-only HEAD~1 HEAD)

for file in $changed_files; do
    if [[ $file == *.ssp ]]; then
        echo "file: $file"
        folder=$(dirname "$file")
        echo "folder: $folder"
        manifest_file="manifest.json"   
        if [ -f "$manifest_file" ]; then
            echo "inside manifest"
            typee=$(jq -r '.schema' "$manifest_file")
            echo "typee: $typee" 

            type="component"
            name=$(jq -r '.name' "$manifest_file")
            title=$(jq -r '.title' "$manifest_file")
            description=$(jq -r '.description' "$manifest_file")
            version=$(jq -r '.version' "$manifest_file")

            logo="$folder/logo.png"
            if [[ -f "$logo" ]]; then
                # Resize logo.png to 240x240 pixels
                convert "$logo" -resize 240x240! "$logo"
                echo "Resized logo.png to 240x240 pixels"
            else
                echo "Current Working Directory: $(pwd)"
                echo "logo.png not found in $folder"
                echo "Listing files in $folder:"
                ls -lah "$folder"
                exit 1
            fi
        
            if [ -z "$repo" ] || [ -z "$type" ] || [ -z "$name" ] || [ -z "$title" ] || [ -z "$description" ] || [ -z "$version" ] ; then
                echo "Error: One or more required fields are empty or not found in $manifest_file"
                exit 1
            fi
            python publish.py --repo-dir "$folder" --title "$title" --name "$name" --title "$title" --description "$description" --type "$type" --version "$version" --logo "$logo"
        fi

    fi
done          
IFS="$original_ifs"
