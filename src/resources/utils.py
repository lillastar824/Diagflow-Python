from dfcx_scrapi.builders.entity_types import EntityTypeBuilder
from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.entity_types import EntityTypes
from google.cloud.dialogflowcx_v3beta1 import types

from resources.entity_types import ENTITY_TYPES
from utils import Config


def build_entities(list: dict[str, list[str]]):
    new_entities = []
    for et_list_name, et_list in list.items():
        new_entity = types.EntityType.Entity(
            value=et_list_name, synonyms=et_list
        )
        new_entities.append(new_entity)
    return new_entities


class Resources:
    def __init__(self, config: Config):
        self.config = config
        self.agents_instance = Agents(creds_path=config.service_account_key)
        self.agent_path = self.get_agent_path(config.agent_display_name)

    def get_agent_path(self, display_name: str):
        agent_obj = self.agents_instance.get_agent_by_display_name(
            project_id=self.config.project_id,
            display_name=display_name,
        )
        if agent_obj is None:
            agent_obj = self.agents_instance.create_agent(
                project_id=self.config.project_id,
                display_name=display_name,
            )
        return agent_obj.name

    def restore_agent(self):
        agents_instance = Agents(creds_path=self.config.service_account_key)
        uri = self.config.gcs_bucket_uri_to_restore
        print(f"Restoring agent from {uri}")
        lro_response = agents_instance.restore_agent(
            agent_id=self.agent_path,
            gcs_bucket_uri=self.config.gcs_bucket_uri_to_restore,
        )
        print("Agent restored", lro_response)

    def create_entity_types(self):
        et_instance = EntityTypes(agent_id=self.agent_path)
        et_map = et_instance.get_entities_map(reverse=True)

        for et_display_name, et_lists in ENTITY_TYPES.items():
            new_entities = build_entities(et_lists)
            try:
                et_id = et_map[et_display_name]
                et_obj: types.EntityType = et_instance.get_entity_type(
                    entity_id=et_id
                )
                et_obj.entities.clear()
                et_obj.entities.extend(new_entities)
                et_instance.update_entity_type(
                    entity_type_id=et_id, obj=et_obj
                )
            except KeyError:
                print(f"Entity Type {et_display_name} not found")
                et_builder = EntityTypeBuilder().create_new_proto_obj(
                    kind=types.EntityType.Kind.KIND_MAP,
                    display_name=et_display_name,
                )
                et_builder.entities.extend(new_entities)
                et_instance.create_entity_type(
                    agent_id=self.agent_path, obj=et_builder
                )
                pass
            except Exception as e:
                print(e)
                continue
