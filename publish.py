import argparse
import base64
import json
import os
import pathlib
import requests
import sys
import tempfile

from zipfile import ZipFile, ZIP_DEFLATED

parser = argparse.ArgumentParser(description='Packages up a solution/component SSP')
parser.add_argument('--repo-dir',    required=True,  help='Full path in the repo where the solution/component is located', type=pathlib.Path)
parser.add_argument('--title',       required=True,  help='The title of the solution/component')
parser.add_argument('--description', required=True,  help='The title of the solution/component')
parser.add_argument('--name',        required=True,  help='The name of the solution/component')
parser.add_argument('--type',        required=True,  help='Either "component" or "solution"')
parser.add_argument('--logo',        required=True,  help='Full path to the logo to use')
parser.add_argument('--version',     required=True,  help='Version of the content')
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
    if args.type not in ('component', 'solution'): 
        print('Error: The --type arg must be either "component" or "solution"')
        sys.exit(-1)

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
    if not os.path.exists(manifest_file):
        print('Error: path "{0}" does not contain a manifest.json file'.format(args.repo_dir))
        sys.exit(-1)

    readme_file = os.path.join(args.repo_dir, 'README.md')
    if not os.path.exists(readme_file):
        print('Error: no README.md file found in "{0}"'.format(args.repo_dir))
        sys.exit(-1)

    docs_file = os.path.join(args.repo_dir, 'documentation.README.md')
    if not os.path.exists(docs_file):
        print('Error: no documentation.README.md file found in "{0}"'.format(args.repo_dir))
        sys.exit(-1)

    if not os.path.exists(args.logo):
        print('Error: logo file "{0}" does not exist'.format(args.logo))
        sys.exit(-1)

    manifest = json.load(open(manifest_file))

    manifest['schema'] = 'component/1' if args.type == 'component' else 'solution/1'
    manifest['author'] = 'Swimlane'
    manifest['name'] = args.name
    manifest['title'] = args.title
    manifest['version'] = args.version
    manifest['description'] = args.description
    manifest['readme'] = get_base64_encoded_file_contents(readme_file)
    manifest['docs'] = get_base64_encoded_file_contents(docs_file)
    manifest['iconImage'] = get_base64_encoded_file_contents(args.logo)

    with open(manifest_file, "w") as output:
        output.write(json.dumps(manifest, indent=2))

def package_ssp(args, temp_dir):
    directory = pathlib.Path(temp_dir)
    zip_file = os.path.join(args.repo_dir, "{0}-{1}-{2}-packaged.ssp".format(args.name, args.type, args.version))

    with ZipFile(zip_file, 'w', ZIP_DEFLATED, compresslevel=9) as archive:
        for path in directory.rglob('*'):
            archive.write(path, arcname=path.relative_to(directory))

    return zip_file

def upload_ssp(args, filename):
    publish_url = args.publish_url
    # Need to exchange username/password for auth token before we can upload
    login_url = '{0}/api/auth/login'.format(publish_url)
    auth = {'username': args.username, 'password': args.password}
    response = requests.post(login_url, json=auth)

    if response.status_code != requests.codes.ok:
        print('Error: Unable to login to {0}'.format(publish_url))
        sys.exit(-1)

    json_response = response.json()
    token = json_response["accessToken"]

    # Upload the actual SSP
    uri_fragment = 'components' if args.type == 'component' else 'solutions'
    upload_url = '{0}/api/indexing/{1}'.format(publish_url, uri_fragment)
    payload = {'file': open(filename, 'rb')}
    headers = {'Authorization': 'bearer ' + token}
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