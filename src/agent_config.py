import os

from dfcx_scrapi.core.agents import Agents
from dfcx_scrapi.core.flows import Flows
from google.cloud.dialogflowcx_v3beta1.types import (
    AdvancedSettings,
    Flow,
    GcsDestination,
    NluSettings,
    SpeechToTextSettings,
    SsmlVoiceGender,
    SynthesizeSpeechConfig,
)

import utils


def init(config: utils.Config):
    agent_instance = Agents(creds_path=config.service_account_key)
    agent_id = utils.get_agent_id(config)
    agent_obj = agent_instance.get_agent(agent_id=agent_id)

    update_data = {
        "speech_to_text_settings": SpeechToTextSettings(
            enable_speech_adaptation=True,
        ),
        "text_to_speech_settings": {
            "synthesize_speech_configs": {
                "en": SynthesizeSpeechConfig(
                    {
                        "voice": {
                            "name": "en-US-Neural2-C",
                            "ssml_gender": (
                                SsmlVoiceGender.SSML_VOICE_GENDER_FEMALE
                            ),
                        }
                    }
                )
            }
        },
        "advanced_settings": AdvancedSettings(
            {
                "audio_export_gcs_destination": GcsDestination(
                    uri=os.environ["AUDIO_EXPORT_GCS_URL"]
                ),
                "dtmf_settings": {
                    "enabled": True,
                    "max_digits": 10,
                    "finish_digit": "#",
                },
                "logging_settings": {
                    "enable_stackdriver_logging": True,
                    "enable_interaction_logging": True,
                },
            }
        ),
    }
    agent_instance.update_agent(
        agent_id=agent_id, obj=agent_obj, **update_data
    )


def update_flow_settings(config: utils.Config):
    agent_id = utils.get_agent_id(config)
    flows = Flows()
    flows_map = flows.get_flows_map(agent_id=agent_id, reverse=True)
    nlu_settings_model_type = NluSettings.ModelType.MODEL_TYPE_ADVANCED
    for flow_display_name, flow_id in flows_map.items():
        flow_obj: Flow = flows.get_flow(flow_id=flow_id)
        if flow_obj.nlu_settings.model_type == nlu_settings_model_type:
            continue
        flow_obj.nlu_settings.model_type = nlu_settings_model_type
        flows.update_flow(flow_id=flow_id, obj=flow_obj)
        print("Updated flow: ", flow_display_name, end="\n")
