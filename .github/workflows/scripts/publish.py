import argparse
import base64
import json
import os
import pathlib
from pyclbr import Class
import requests
import sys
import tempfile
from glob import glob

from zipfile import ZipFile, ZIP_DEFLATED

class VIC:
    name = ""
    title = ""
    description = ""
    type = ""
    logo = ""
    readme = ""
    doc_readme = ""
    version = ""
    manifest = ""
        
    def __init__(self) -> None:        
        pass

parser = argparse.ArgumentParser(description='Packages up a solution/component SSP')
parser.add_argument('--repo-dir',    required=True,  help='Full path in the repo where the solution/component is located', type=pathlib.Path)
parser.add_argument('--publish', action='store_true',help='Whether or not to publish the content to Marketplace')
parser.add_argument('--publish_url')
parser.add_argument('--username')
parser.add_argument('--password')

def validate_publish_args(args):
    if args.publish is not True:
        return
    
    if args.publish_url is None:
        print('Error: The --publish_url arg is required when --publish flag is supplied')
        sys.exit(-1)

    if args.username is None:
        print('Error: The --username arg is required when --publish flag is supplied')
        sys.exit(-1)

    if args.password is None:
        print('Error: The --password arg is required when --publish flag is supplied')
        sys.exit(-1)

def validate_args(args):
    print("validate_args")
    repo_dir = args.repo_dir

    if not os.path.exists(repo_dir):
        print('Error: path "{0}" does not exist'.format(repo_dir))
        sys.exit(-1)

    # os.chdir(repo_dir)     
    dir_list = os.listdir(repo_dir)

    if not 'manifest.json' in dir_list:
        print('Error: manifest.json does not exist in "{0}"'.format(repo_dir))
        sys.exit(-1)        
    VIC.manifest = os.path.join(repo_dir, 'manifest.json')


    _logo = glob(os.path.join(args.repo_dir, 'logo*'))
    if len(_logo) == 0:
        print('Error: logo does not exist in "{0}"'.format(repo_dir))
        sys.exit(-1)
    if len(_logo) > 1:
        print('Error: multiple logo files exist in "{0}"'.format(repo_dir))
        sys.exit(-1)        
    VIC.logo = os.path.join(repo_dir, _logo[0])
        
    if not 'README.md' in dir_list:
        print('Error: no README.md file found in "{0}"'.format(repo_dir))
        sys.exit(-1)
    VIC.readme = os.path.join(repo_dir, 'README.md')

    if not 'documentation.README.md' in dir_list:
        print('Error: no documentation.README.md file found in "{0}"'.format(repo_dir))
        sys.exit(-1)
    VIC.doc_readme = os.path.join(repo_dir, 'documentation.README.md')
    
    validate_publish_args(args)

def find_ssp_file(repo_dir):
    ssp_file = None
    for file in os.listdir(repo_dir):
        if file.endswith('.ssp'):
            ssp_file = os.path.join(repo_dir, file)
            break

    if ssp_file == None:
        print('Error: path "{0}" does not contain an SSP file'.format(repo_dir))
        sys.exit(-1)

    return ssp_file



def extract_ssp_file_to_temp_dir(ssp_file):
    temp_dir = tempfile.mkdtemp()
    with ZipFile(ssp_file, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    return temp_dir

def get_base64_encoded_file_contents(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode('utf-8')

def update_manifest(temp_dir, args):
    
    manifest_file = os.path.join(temp_dir, 'manifest.json')
    repo_manifest_file = VIC.manifest
    if not os.path.exists(manifest_file):
        print('Error: path "{0}" does not contain a manifest.json file'.format(args.repo_dir))
        sys.exit(-1)

    manifest = json.load(open(manifest_file))
    repo_manifest = json.load(open(repo_manifest_file))     
    print(repo_manifest_file)
    print(repo_manifest)
    VIC.type = repo_manifest.get('schema')[:-2].lower()
    VIC.name = repo_manifest.get('name')
    VIC.description = repo_manifest.get('description')
    VIC.version = repo_manifest.get('version')
    VIC.title = repo_manifest.get('title')
    print(VIC.type)

    if not (VIC.type == "component" or VIC.type != "solution"):         
        print('Error: The manifest type must be either "component" or "solution"')
        sys.exit(-1)

    manifest['schema'] = 'component/1' if VIC.type == 'component' else 'solution/1'
    manifest['author'] = 'Swimlane'
    manifest['name'] = VIC.name
    manifest['title'] = VIC.title
    manifest['version'] = VIC.version
    manifest['description'] = VIC.description
    manifest['readme'] = get_base64_encoded_file_contents(VIC.readme)
    manifest['docs'] = get_base64_encoded_file_contents(VIC.doc_readme)
    manifest['iconImage'] = get_base64_encoded_file_contents(VIC.logo)

    with open(manifest_file, "w") as output:
        output.write(json.dumps(manifest, indent=2))

def package_ssp(args, temp_dir):
    directory = pathlib.Path(temp_dir)
    zip_file = os.path.join(args.repo_dir, "{0}-{1}-{2}-packaged.ssp".format(VIC.name, VIC.type, VIC.version))

    with ZipFile(zip_file, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in directory.rglob('*'):
            archive.write(path, arcname=path.relative_to(directory))

    return zip_file

def upload_ssp(args, filename):
    publish_url = args.publish_url
    # Need to exchange username/password for auth token before we can upload
    loginHeaders =  {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "gh-actions",
    }
    login_url = '{0}/api/auth/login'.format(publish_url)
    auth = {'username': args.username, 'password': args.password}
    response = requests.post(login_url, json=auth, headers=loginHeaders)

    if response.status_code != requests.codes.ok:
        print('Error: Unable to login to {0}'.format(publish_url))
        sys.exit(-1)

    json_response = response.json()
    token = json_response["accessToken"]
    print(token)

    # Upload the actual SSP
    uri_fragment = 'components' if args.type == 'component' else 'solutions'
    upload_url = '{0}/api/indexing/{1}'.format(publish_url, uri_fragment)
    payload = {'file': open(filename, 'rb')}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "gh-actions",
        'Authorization': 'bearer ' + token
    }
    response = requests.post(upload_url, files=payload, headers=headers)

    if response.status_code != 201: # Is there a requests.codes alias for 201?
        print('Error: Unable to upload SSP to {0}'.format(upload_url))
        sys.exit(-1)

    return upload_url

def main():
    args = parser.parse_args()
    
    validate_args(args)

    ssp_file = find_ssp_file(args.repo_dir)
    temp_dir = extract_ssp_file_to_temp_dir(ssp_file)
    update_manifest(temp_dir, args)
    zip_file = package_ssp(args, temp_dir)

    print('Saved as {0}'.format(zip_file))

    if args.publish:
        upload_url = upload_ssp(args, zip_file)
        print('Published {0} to {1}'.format(os.path.basename(zip_file), upload_url))

main()