from enum import Enum

from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.routes import (  # noqa: E501
    EventHandlerBuilder,
    TransitionRouteBuilder,
)
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages
from dfcx_scrapi.core.webhooks import Webhooks
from google.cloud.dialogflowcx_v3beta1.types import Webhook

import commons
import utils


class DefaultStartPageNames(str, Enum):
    END_ESCALATE_COORDINATOR = "end escalate COORDINATOR"


def create_default_start_flow_pages(
    config: utils.Config,
    flow_display_name="Default Start Flow",
):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    try:
        flow_obj = flows_instance.get_flow_by_display_name(
            flow_display_name, agent_id
        )
    except ValueError as e:
        utils.logger.debug(e)
    except Exception as e:
        utils.logger.error(e)
        raise

    pages_instance = Pages(creds_path=config.service_account_key)
    pages_to_create = [page.value for page in DefaultStartPageNames]

    builder_map = {}
    for page in pages_to_create:
        page_builder = PageBuilder()
        page_builder.create_new_proto_obj(display_name=page, overwrite=True)
        builder_map[page] = page_builder
    for page_display_name, builder in builder_map.items():
        try:
            pages_instance.create_page(
                obj=builder.proto_obj, flow_id=flow_obj.name
            )
        except Exception as e:
            print(e)
            pass

    flows_map = flows_instance.get_flows_map(agent_id, reverse=True)
    page_map = pages_instance.get_pages_map(
        flows_map[flow_display_name], reverse=True
    )

    wh_error_eh = EventHandlerBuilder().create_new_proto_obj(
        event="webhook.error",
        target_page=page_map[DefaultStartPageNames.END_ESCALATE_COORDINATOR],
        overwrite=True,
    )

    if not utils.is_existing_event_handler(
        wh_error_eh, flow_obj.event_handlers
    ):
        flow_obj.event_handlers.extend([wh_error_eh])

    flow_failed_eh = EventHandlerBuilder().create_new_proto_obj(
        event="flow.failed.human-escalation",
        target_page=page_map[DefaultStartPageNames.END_ESCALATE_COORDINATOR],
        overwrite=True,
    )
    if not utils.is_existing_event_handler(
        flow_failed_eh, flow_obj.event_handlers
    ):
        flow_obj.event_handlers.extend([flow_failed_eh])

    intents_instance = Intents()
    intents_map = intents_instance.get_intents_map(agent_id, True)

    webhooks_instance = Webhooks(agent_id=agent_id)
    wh_upser_data_into_spanner = (
        utils.WebHookNames.UPSERT_DATA_INTO_SPANNER.value
    )

    #  Creating webhook
    try:
        webhooks_instance.get_webhook_by_display_name(
            wh_upser_data_into_spanner
        )
    except ValueError:
        utils.logger.info(
            "Creating webhook %s ...", wh_upser_data_into_spanner
        )
        webhook_obj = Webhook()
        webhook_obj.display_name = wh_upser_data_into_spanner
        wh_upsert_data_into_spanner = (
            utils.WebHookNames.UPSERT_DATA_INTO_SPANNER
        )
        webhook_obj.generic_web_service.uri = utils.get_webhook_uri(
            wh_upsert_data_into_spanner
        )
        webhooks_instance.create_webhook(agent_id=agent_id, obj=webhook_obj)
        pass
    except Exception as e:
        utils.logger.error(e)
        raise

    webhook_map = webhooks_instance.get_webhooks_map(
        agent_id=agent_id, reverse=True
    )
    default_welcome_intent_fmt_builder = utils.create_fulfillment_builder(
        webhook=webhook_map[wh_upser_data_into_spanner],
        tag="conversation_started",
        # paramter presents only accepts string so with tricks we set array
        # and boolean values
        parameter_presets={
            "human_escalated": False,  # set false
            "wrap_codes": [],  # set empty arr
            "cid": "$session.params.callerANI",
            "did": "$session.params.DNIS",
            "premature_hang_up": True,  # set true
            "genesys_conversation_id": "$session.params.conversationId",
            "genesys_communication_id": "$session.params.communicationId",
            "transfer_reason": "",
            "friendly_practice_name": "this practice",
            "genesysAuthenticated": "Authentication failed",
            "genesysEMRLink": "",
            "resourceMatrixLink": "",
            "head_intent": "Unknown",
            "genesysPatientDateOfBirth": "Authentication failed",
            "genesysPatientName": "Authentication failed",
            "queueId": "$session.params.queueName",
            "denimSuccessfullyCompleted": "false",
            "transfering_agent_message": commons.TRANSFERRING_TO_AGENT_FAILED,
        },
        # response_message={
        #     "message": commons.DEFAULT_WELCOME_INTENT_HELLO,
        #     "type": "text",
        # },
    )

    default_welcome_intent_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[utils.IntentNames.DEFAULT_WELCOME_INTENT],
        trigger_fulfillment=default_welcome_intent_fmt_builder.proto_obj,
        overwrite=True,
    )
    human_escalation_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[
            utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT
        ],
        target_page=page_map[DefaultStartPageNames.END_ESCALATE_COORDINATOR],
        overwrite=True,
    )

    scheduling_flow_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        target_flow=flows_map[utils.FlowNames.SCHEDULING],
        trigger_fulfillment=utils.create_fulfillment_builder(
            response_message={
                "message": commons.PROMPT_FOR_SCHEDULING,
                "type": "text",
            },
        ).proto_obj,
    )

    flow_obj.transition_routes.clear()
    tr_extends = [
        default_welcome_intent_tr,
        human_escalation_tr,
        scheduling_flow_tr,
    ]
    flow_obj.transition_routes.extend(tr_extends)

    eec_page_entry_fmt_builder = utils.create_fulfillment_builder(
        webhook=webhook_map[wh_upser_data_into_spanner],
        tag="human_escalate",
        parameter_presets={
            "human_escalated": True,
            "premature_hang_up": False,
            "wrap_codes": "$sys.func.APPEND($session.params.wrap_codes, "
            '"agent_escalated")',
        },
        response_message={
            "message": "$session.params.transfering_agent_message",
            "type": "text",
        },
    )
    response_message_args = utils.ResponseMessageArgs(
        type="live_agent_handoff",
        message={
            "metaData": {
                "dob": "$session.params.genesysPatientDateOfBirth",
                "authenticated": "$session.params.genesysAuthenticated",
                "intent": "$session.params.head_intent",
                "name": "$session.params.genesysPatientName",
                "emrLink": "$session.params.genesysEMRLink",
                "rmLink": "$session.params.resourceMatrixLink",
            }
        },
    )
    transfer_to_agent_fullfilment = utils.create_fulfillment_builder(
        webhook=None,
        tag=None,
        parameter_presets=None,
        response_message=response_message_args,
    ).proto_obj

    end_escalation_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            trigger_fulfillment=transfer_to_agent_fullfilment,
            target_page=utils.get_symbolic_page(
                flow_obj.name,
                utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
            ).name,
        )
    )

    builder_map[
        DefaultStartPageNames.END_ESCALATE_COORDINATOR
    ].proto_obj.entry_fulfillment = eec_page_entry_fmt_builder.proto_obj

    builder_map[
        DefaultStartPageNames.END_ESCALATE_COORDINATOR
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100, "\n")
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
