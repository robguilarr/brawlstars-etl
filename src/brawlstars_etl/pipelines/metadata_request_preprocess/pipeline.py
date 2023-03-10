"""
This is a boilerplate pipeline 'metadata_request_preprocess'
generated using Kedro 0.18.4
"""
from kedro.pipeline import Pipeline, node, pipeline
from .nodes import players_info_request

def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=players_info_request,
                inputs=['player_tags_txt','params:players_info_request'],
                outputs='raw_players_info@pandas',
                name='players_info_request_node'
            )
        ]
    )
