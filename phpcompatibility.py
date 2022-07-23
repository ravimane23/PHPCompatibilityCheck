import subprocess
import json
import shutil
import os
import sys
import pathlib
from os import path

# download pandas module if not available in the system.
#if 'pandas' in sys.modules == False:
#	subprocess.run('pip3 install pandas', shell=True) 
import pandas as pd

class DrupalStandardsRun:
	PATCH_DIR = ''
	MODULE_DIR = ''
	COMPATIBILITY_ERROR_DIR = ''
	PLATFPOM_MODULES = ''

	def __init__(self):
		print('Checking Settings...')
		self.PATCH_DIR = 'phpcs_patches'
		self.MODULE_DIR = 'modules_clone'
		self.COMPATIBILITY_ERROR_DIR = 'phpcs_errors'
		self.CURRENT_DIR = os.getcwd()
		self.folder_exists()
		self.read_csvfile()
		self.process_modules()
 
	def folder_exists(self):
		if not path.exists('vendor'):
			subprocess.call('composer require squizlabs/php_codesniffer --dev', shell=True)
			subprocess.call('composer require phpcompatibility/php-compatibility --dev', shell=True)
			subprocess.call('composer require rector/rector --dev', shell=True)
			subprocess.call('./vendor/bin/rector init', shell=True)
		if not path.exists(self.PATCH_DIR):
			os.mkdir(self.PATCH_DIR)

		if not path.exists(self.MODULE_DIR):
			os.mkdir(self.MODULE_DIR)
		else:
			subprocess.call('rm -rf ' + self.MODULE_DIR + '/*', shell=True)

		if not path.exists(self.COMPATIBILITY_ERROR_DIR):
			os.mkdir(self.COMPATIBILITY_ERROR_DIR)

	def read_csvfile(self):
		print("Reading CSV File")
		# load csv file containg list of contributed modules of drupal 8 platform and core.
		module_list = pd.read_csv('module_list.csv', names=["module_name"])
		platform_module = module_list['module_name'].values.tolist()
		self.PLATFPOM_MODULES = platform_module

	def process_modules(self):
		for value in self.PLATFPOM_MODULES:
			os.chdir(self.CURRENT_DIR)
			name = value.split(" ")
			key = name[0]
			patch_file_name = 'phpcs_'+ key +'.patch'
			file = pathlib.Path(self.PATCH_DIR + '/' + patch_file_name)
			if file.exists():
				print(key + " patch file exist")
			else:
				if not path.exists(self.MODULE_DIR + '/' + key):
					print("Downloading " + key + " module from Drupal ...")
					value = 'git clone --branch ' + name[1] + ' https://git.drupalcode.org/project/' + name[0] + '.git'
					subprocess.call(value, shell=True, cwd=self.MODULE_DIR)

				print('Running Drupal Rector on ' + key + '...')
				drupal_rector = subprocess.run('./vendor/bin/rector process ./' + self.MODULE_DIR + '/' + key, shell=True, stdout=subprocess.PIPE)

				print('Checking Drupal Standards on ' + key + '...')
				drupal_standards_before = self.COMPATIBILITY_ERROR_DIR + '/DrupalStandard-' + key + '-before.txt'
				phpcs_check = subprocess.call('./vendor/bin/phpcs --standard=Drupal --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key + ' > ' + drupal_standards_before, shell=True)

				if phpcs_check != 1:
					print("Resolving Drupal Standards Errors ...")
					drupal_phpcs = subprocess.call('./vendor/bin/phpcbf --standard=Drupal --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key, shell=True, stdout=subprocess.PIPE)

					print("Re-checking Drupal Compatibility on " + key)
					drupal_standards_after = self.COMPATIBILITY_ERROR_DIR + '/DrupalStandard-' + key + '-after.txt'
					phpcs_recheck = subprocess.call('./vendor/bin/phpcs --standard=Drupal --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key + ' > ' + drupal_standards_after, shell=True)

				# PHP_Compatibility PHPCS Check starts here.
				print('Running PHP_Compatibility for PHP 8 ' + key + '..')
				php_compatibility_before = self.COMPATIBILITY_ERROR_DIR + '/PHPStandard-' + key + '-before.txt'
				php74_check = subprocess.call('./vendor/bin/phpcs --standard=PHPCompatibility --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key + ' > ' + php_compatibility_before, shell=True)

				if php74_check != 1:
					# PHP_Compatibility PHPCS Check starts here.
					print('Resolving PHP_Compatibility for PHP 8 on ' + key + '..')
					php74_check = subprocess.call('./vendor/bin/phpcbf --standard=PHPCompatibility --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key, shell=True, stdout=subprocess.PIPE)

					# PHP_Compatibility PHPCS Check starts here.
					print('Re-checking PHP_Compatibility for PHP 8 on ' + key + '..')
					php_compatibility_after = self.COMPATIBILITY_ERROR_DIR + '/PHPStandard-' + key + '-after.txt'
					php74_check = subprocess.call('./vendor/bin/phpcs --standard=PHPCompatibility --runtime-set testVersion 8.0 --extensions=php,module,inc,install,test,profile,theme,css,info,txt,md,yml ' + self.MODULE_DIR + '/'+ key + ' > ' + php_compatibility_after, shell=True)

			print("Creating Patch for " + key + " module")
			os.chdir(self.MODULE_DIR + '/' + key)
			git_status = subprocess.run(['git', 'status'], stdout=subprocess.PIPE)
			if git_status.stdout.decode('utf-8').find('nothing to commit, working tree clean') != -1:
				print('Nothing to commit, exiting..', 'status')
				log = open(key + '.patch', 'w')
				log.write("Module is fully compatible with PHP 8")
				log.flush()
			else:
				print('PR creation in process..', 'info')
				log = open(patch_file_name, 'w')
				log.flush() 
				proc = subprocess.run(['git', 'diff'], stdout=log)
				subprocess.call('cp ' + patch_file_name + ' ../../' + self.PATCH_DIR + '/', shell=True)
				os.chdir('../../')

			print(key + " Modules completed ...")

DrupalStandardsRun()