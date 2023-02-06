"""
This is a boilerplate pipeline 'metadata_request_preprocess'
generated using Kedro 0.18.4
"""
# General dependencies
import pandas as pd
import brawlstats
# Parameters definitions
from typing import Any, Dict, Tuple
# To load the configuration (https://kedro.readthedocs.io/en/stable/kedro_project_setup/configuration.html#credentials)
from kedro.config import ConfigLoader
from kedro.framework.project import settings
conf_loader_local = ConfigLoader(conf_source= settings.CONF_SOURCE, env= 'local')
conf_credentials = conf_loader_local['credentials']
# Logging
import time
import logging
log = logging.getLogger(__name__)
# Async processes
import asyncio

def players_info_request(player_tags_txt: str,
                         parameters : Dict
) -> pd.DataFrame:
    '''
    Extracts Players metadata from Brawlstars API by executing an Async Event Loop over a list of futures objects.
    These are made of task objects built of Async threads due blocking call limitations of api_request sub_module.
    Args:
        player_tags: PLayer tag list
    Returns:
        All players metadata concatenated into a structured Dataframe
    '''
    # Get key and validate it exists
    API_KEY = conf_credentials.get('brawlstars_api', None).get('API_KEY', None)
    try:
        assert API_KEY != None
    except AssertionError:
        log.info("No API key has been defined. Request one at https://developer.brawlstars.com/")

    # Create client object from brawlstats API wrapper, be aware of preventing the rate limit for huge requests,
    # review prevent_ratelimit in the source code
    client = brawlstats.Client(token=API_KEY)

    # Create list of player tags, from catalog
    player_tags_txt = player_tags_txt.split(',')

    def api_request(tag: str) -> pd.DataFrame:
        '''Request player data from the Brawl Stars API and give a structured format'''
        try:
            # Extract player information based on https://brawlstats.readthedocs.io/en/latest/api.html#player
            player_metadata = client.get_player(tag).raw_data
            # Normalize data in structured format
            player_metadata_structured = pd.json_normalize(player_metadata)
            player_metadata_structured.rename({'tag':'player_id'}, axis= 1, inplace=True)
        except:
            log.info(f"No Metadata extracted for player {tag}")
            player_metadata_structured = pd.DataFrame()
            pass
        return player_metadata_structured

    async def api_request_async(tag: str) -> pd.DataFrame:
        '''
        Transform non-sync request function to async coroutine, which creates
        a future object by API request.
        The Coroutine contains a blocking call that won't return a log until it's complete. So,
        to run concurrently, await the thread and not the coroutine by using this method.
        '''
        return await asyncio.to_thread(api_request, tag)

    async def spawn_request(player_tags: list) -> pd.DataFrame:
        '''Use gathering to request player metadata as async tasks objects, made of coroutines'''
        start = time.time()
        log.info(f"PLayer info request process started")
        # Comprehensive list of coroutines as Task Objects, whom will be already scheduled its execution
        requests_tasks = [asyncio.create_task(api_request_async(tag)) for tag in player_tags]
        # Future Object: List of battlelogs as Dataframes
        player_metadata_list = await asyncio.gather(*requests_tasks)
        # When all tasks all executed, concat all dataframes into one
        player_metadata = pd.concat(player_metadata_list, ignore_index=True)
        log.info(f"PLayer info request process Finished in {time.time() - start} seconds")
        return player_metadata

    def activate_request(n: int = None) -> pd.DataFrame:
        '''Run the events-loop, check for request limit defined by user'''
        if n:
            player_metadata = asyncio.run(spawn_request(player_tags_txt[:n]))
        else:
            player_metadata = asyncio.run(spawn_request(player_tags_txt))
        return player_metadata

    player_metadata = activate_request(n= parameters['metadata_limit'])

    # Validate concurrency didn't affect the data request
    try:
        assert not player_metadata.empty
    except AssertionError:
        log.info("No Metadata was extracted. Please check your Client Connection")

    return player_metadata