# A session-independent cache for DocuSign Recipes

# Use this file to store information that needs to be available independent
# of a particular user's session.
# This is especially needed for credentials for "Service Integration" that just
# run in the background.

# Set encoding to utf8. See http:#stackoverflow.com/a/21190382/64904 
import sys; reload(sys); sys.setdefaultencoding('utf8')
from flask import request, session
from app.lib_master_python import ds_cache_defaults


# Global constants


########################################################################
########################################################################
########################################################################

def get():
    """ Get the current value of the cache, or the defaults
    
        Returns: a dictionary of the cache
    """
    
    # We don't yet the updatable version of the cache implemented, so
    # just use the defaults
        
    return ds_cache_defaults.get()


########################################################################
########################################################################
########################################################################


## FIN ##

