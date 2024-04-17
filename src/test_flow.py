from enum import Enum

from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents

import commons
import utils


class FlowNames(str, Enum):
    CONFIRM_BLOCK = "Confirm Block"


def create_flow_pages(
    config: utils.Config,
    flow_display_name="[TEMP] Test Flow",
):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    flows_map = flows_instance.get_flows_map(agent_id=agent_id, reverse=True)
    try:
        flow_obj = flows_instance.get_flow_by_display_name(
            flow_display_name, agent_id
        )
    except ValueError:
        flow_obj = utils.create_fake_flow(
            config,
            flow_display_name,
        )
        pass
    except Exception as e:
        utils.logger.error(e)
        raise

    default_welcome_intent_fmt_builder = utils.create_fulfillment_builder(
        response_message={
            "message": commons.DEFAULT_WELCOME_INTENT_HELLO,
            "type": "text",
        },
        parameter_presets={
            "confirm_text": commons.CONFIRM_BLOCK_PROMPT,
        },
    )

    intents_instance = Intents()
    intents_map = intents_instance.get_intents_map(agent_id, True)
    default_welcome_intent_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[utils.IntentNames.DEFAULT_WELCOME_INTENT],
        trigger_fulfillment=default_welcome_intent_fmt_builder.proto_obj,
        overwrite=True,
    )

    flow_cb_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        target_flow=flows_map[FlowNames.CONFIRM_BLOCK],
    )
    flow_obj.transition_routes.clear()
    flow_obj.transition_routes.extend([default_welcome_intent_tr, flow_cb_tr])

    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
