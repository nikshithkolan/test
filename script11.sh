          original_ifs="$IFS"
          IFS=$'\n'
          changed_files=$(git diff --name-only HEAD~1 HEAD)
          echo "hello"

          for file in $changed_files; do
              if [[ $file == *.ssp ]]; then
                  folder=$(dirname "$file")
                  cd $folder
                  repo_dir=$(pwd)

                  python ../scripts/publish.py --repo-dir "$repo_dir" --publish --publish_url ${{ env.MARKETPLACE_URL }}  --username ${{ secrets.MARKETPLACE_USERNAME }} --password ${{ secrets.MARKETPLACE_PASSWORD }}
                  cd -
                  fi
        done          
        IFS="$original_ifs"

