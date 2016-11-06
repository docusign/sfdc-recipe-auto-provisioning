#!/bin/sh
#
# Goal: Make a Heroku version of this directory.
# 
# Since Heroku requires that the git repo contain the application at
# the root level of the repo, we create a new git repo and
# copy the relevant files and directory structure from here to there.
# 
# Usage: build_heroku.sfdc-recipe-auto-provisioning.sh target_directory
# The target_directory MUST NOT be within the directory that contains
# this file (or a subdirectory of it.)
#
# 

############################################
#
# Functions
#
# matches
#
# Usage
# if matches input pattern; then
# (without the [ ]).
matches() {
    input="$1"
    pattern="$2"
    echo "$input" | grep -q "$pattern"
}

############################################
#
# Main line...

echo ""
RECIPE=$0
TARGET_DIR=$1
SCRIPT=$0
SCRIPT_ORIG=$0
HEROKU_NAME=$2
# Set force (value of 0 means force is true (sh standard))
[ "$3" == "-force" ] 
FORCE=$?

# check that we're in the directory with the script file.
SCRIPT=`basename $SCRIPT`
if [ $SCRIPT_ORIG != "./${SCRIPT}" ]; then
	echo "*** Problem: You must execute the command from within the recipe's directory"
	echo "    Invoke via ./${SCRIPT}"
	echo "    "
	echo "    Example: ./${SCRIPT} .. <heroku_name>   or   ./${SCRIPT} .. <heroku_name> -force"    
	exit 1
fi

# Argument present?
if [ "$1" == "" ]; then
    echo ""
	echo "*** Usage:  $SCRIPT target_directory heroku_name [-force]"
    echo "    The target_directory will be the owning directory for the Heroku repo"	
    echo "    The target_directory MUST NOT be in an existing repo"
	echo "    or within the directory that contains this file (or a subdirectory of it.)"
	echo "    -force  -- the script will remove an existing target repo"
	echo "    "
	echo "    Example: ./${SCRIPT} <heroku_name> ..    or   ./${SCRIPT} .. <heroku_name> -force"    
	exit 1
fi

if [ "$2" == "" ]; then
    echo ""
	echo "*** Missing heroku name"
	echo "    Example: ./${SCRIPT} <heroku_name> ..    or   ./${SCRIPT} .. <heroku_name> -force"    
	exit 1
fi


# the script name is something like 010.build_heroku.webhook_php.sh
# Get the recipe's name:
RECIPE=`basename $RECIPE .sh`
RECIPE=`echo $RECIPE | sed -e "s/build_heroku\.//"`
printf 'Creating Heroku Git repo for recipe: %s\n' "${RECIPE}"

RECIPE_REPO="heroku_${RECIPE}"
echo "New repo name: $RECIPE_REPO"

CURRENT_DIR=`pwd`
TARGET_DIR=$(cd $TARGET_DIR 2>/dev/null; pwd) # change to absolute path
printf 'Target owning directory: %s\n' "${TARGET_DIR}"
RECIPE_REPO_ABS=${TARGET_DIR}/${RECIPE_REPO}
printf 'Target repo directory: %s\n' "${RECIPE_REPO_ABS}"

if matches $TARGET_DIR $CURRENT_DIR; then
    echo ""
	echo "*** Problem: the target_directory is within the current dir!"
    echo "*** Please choose a target directory that is not below $CURRENT_DIR"
	exit 1
fi

if GPATH=`cd $TARGET_DIR;git rev-parse --show-toplevel --quiet 2>/dev/null`; then
    echo ""
	echo "*** Problem: the target_directory is in an existing Git repo!"
    echo "*** Existing repo: $GPATH"
	exit 1
fi

if [ ! -d "$RECIPE_REPO_ABS" ]; then
  # Make the target dir
  printf "%%%%%% Creating %s ... " $RECIPE_REPO_ABS
  mkdir $RECIPE_REPO_ABS || exit 1
  printf "done\n"
else
  # Hmmm, directory exists. If -force, then delete the directory
  echo "The target repo directory already exists."
  if [ "$FORCE" -eq "0" ]; then
	  printf "%%%%%% Removing existing directory %s ... " $RECIPE_REPO_ABS
	  rm -rf $RECIPE_REPO_ABS || exit 1 
	  printf "done\n"  	
	  printf "%%%%%% Creating an empty directory there ... "
	  mkdir $RECIPE_REPO_ABS || exit 1
	  printf "done\n"
  else
	  echo "*** Either remove the existing repo directory or use -force option"
	  exit 1
  fi
fi

# import user's path so heroku can be found
source ~/.profile

# Check that Heroku and git are installed
which heroku > /dev/null
if [ $? -ne "0" ]; then
	echo "*** heroku command not found!"
	echo "    See https://devcenter.heroku.com/start to install it"
	exit 1
fi

which git > /dev/null
if [ $? -ne "0" ]; then
	echo "*** git command not found!"
	exit 1
fi

# copy over the files
printf "%%%%%% Copying files to the new Heroku repo ... "
tar -cvf - . | (cd $RECIPE_REPO_ABS; tar -xf -)

# Remove git-specific files from directories
(cd $RECIPE_REPO_ABS; find . | grep .git | xargs rm -rf)
# Copy just gitignore
cp .gitignore $RECIPE_REPO_ABS
printf "done!\n"

printf "Deploying to Heroku...\n"

printf "%%%%%% Changed to directory %s\n" $RECIPE_REPO_ABS
cd $RECIPE_REPO_ABS

echo "git local add, and commit"
git init
git add .
git commit -m "First commit"
echo "heroku create"
heroku create $HEROKU_NAME --buildpack heroku/python

heroku config:set DEBUG=True

echo "git push heroku master"
git push heroku master
echo "heroku ps:scale web=1"
heroku ps:scale web=1
printf "Working ."
sleep 1; printf "."; sleep 1; printf "."; sleep 1; printf "."; sleep 1; printf ".\n";

printf "\n"
printf "DEBUGGER PIN CODE\n"
#heroku logs # |grep "pin code"
heroku logs | grep code:
printf "\n"

# echo "heroku open"
# heroku open

printf "Heroku temp repo: %s\n" $RECIPE_REPO_ABS

echo ""
echo "The Heroku app name is $HEROKU_NAME"
echo "To tail the log use command heroku logs --tail --app $HEROKU_NAME"
echo "Web hook address for configuring DocuSign Connect:  https://${HEROKU_NAME}.herokuapp.com/webhook_php"
echo ""
heroku logs --tail

exit 0