from enum import Enum

from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.routes import (  # noqa: E501
    EventHandlerBuilder,
    TransitionRouteBuilder,
)
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages

import commons
import test_flow
import utils


class ConfirmBlockPageNames(str, Enum):
    CONFIRM = "> confirm"
    END_ESCALATE = "end escalate"
    END_SUCCESS = "end success"


def create_confirm_block_flow_pages(
    config: utils.Config,
    flow_display_name="Confirm Block",
):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    try:
        flow_obj = flows_instance.get_flow_by_display_name(
            flow_display_name, agent_id
        )
    except ValueError:
        flow_obj = flows_instance.create_flow(
            agent_id=agent_id, display_name=flow_display_name
        )
        pass
    except Exception as e:
        utils.logger.error(e)
        raise

    pages_instance = Pages(creds_path=config.service_account_key)
    pages_to_create = [page.value for page in ConfirmBlockPageNames]

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

    intents_instance = Intents()
    intents_map = intents_instance.get_intents_map(agent_id, True)

    start_page_fmt_builder = utils.create_fulfillment_builder(
        parameter_presets={
            "user_confirmed": None,
        }
    )

    confirm_page_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition="true",
        trigger_fulfillment=start_page_fmt_builder.proto_obj,
        overwrite=True,
        target_page=page_map[ConfirmBlockPageNames.CONFIRM],
    )

    flow_obj.transition_routes.clear()
    tr_extends = [confirm_page_tr]
    flow_obj.transition_routes.extend(tr_extends)

    # confirm page
    confirm_page_entry_fmt_builder = utils.create_fulfillment_builder(
        response_message={
            "message": "$session.params.confirm_text",
            "type": "text",
        },
    )
    builder_map[
        ConfirmBlockPageNames.CONFIRM
    ].proto_obj.entry_fulfillment = confirm_page_entry_fmt_builder.proto_obj

    escalate_human_agent_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[
            utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT
        ],
        target_page=page_map[ConfirmBlockPageNames.END_ESCALATE],
        overwrite=True,
    )
    confirm_yes_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[
            utils.IntentNames.PREBUILT_COMPONENTS_CONFIRMATION_YES
        ],
        trigger_fulfillment=utils.create_fulfillment_builder(
            parameter_presets={
                "user_confirmed": True,
            }
        ).proto_obj,
        target_page=page_map[ConfirmBlockPageNames.END_ESCALATE],
        overwrite=True,
    )
    confirm_no_tr = TransitionRouteBuilder().create_new_proto_obj(
        intent=intents_map[
            utils.IntentNames.PREBUILT_COMPONENTS_CONFIRMATION_NO
        ],
        trigger_fulfillment=utils.create_fulfillment_builder(
            parameter_presets={
                "user_confirmed": False,
            }
        ).proto_obj,
        target_page=page_map[ConfirmBlockPageNames.END_SUCCESS],
        overwrite=True,
    )
    confirm_page_trs = [escalate_human_agent_tr, confirm_yes_tr, confirm_no_tr]

    builder_map[
        ConfirmBlockPageNames.CONFIRM
    ].proto_obj.transition_routes.extend(confirm_page_trs)

    event_handler_messages = utils.EventHandlerMessages(
        no_input_1=commons.CONFIRM_PATTERN_CONFIRM_PAGE_NO_INPUT_1,
        no_input_2=commons.CONFIRM_PATTERN_CONFIRM_PAGE_NO_INPUT_2,
        no_match_1=commons.CONFIRM_PATTERN_CONFIRM_PAGE_NO_MATCH_1,
        no_match_2=commons.CONFIRM_PATTERN_CONFIRM_PAGE_NO_MATCH_2,
    )
    event_handlers = utils.create_event_handlers(
        event_handler_messages,
        end_escalation_page=page_map[ConfirmBlockPageNames.END_ESCALATE],
        page_parameter=True,
    )
    event_handlers.append(
        EventHandlerBuilder().create_new_proto_obj(
            event="flow.failed.human-escalation",
            target_page=page_map[ConfirmBlockPageNames.END_ESCALATE],
            overwrite=True,
        )
    )
    builder_map[ConfirmBlockPageNames.CONFIRM].proto_obj.event_handlers.clear()
    builder_map[ConfirmBlockPageNames.CONFIRM].proto_obj.event_handlers.extend(
        event_handlers
    )

    # end escalate page
    builder_map[
        ConfirmBlockPageNames.END_ESCALATE
    ].proto_obj.transition_routes.extend(
        [
            TransitionRouteBuilder().create_new_proto_obj(
                condition="true",
                overwrite=True,
                target_page=utils.get_symbolic_page(
                    flow_obj.name,
                    utils.SymbolicPages.END_FLOW_WITH_HUMAN_ESCALATION,
                ).name,
            )
        ]
    )

    # end success page
    builder_map[
        ConfirmBlockPageNames.END_SUCCESS
    ].proto_obj.transition_routes.extend(
        [
            TransitionRouteBuilder().create_new_proto_obj(
                condition="true",
                overwrite=True,
                trigger_fulfillment=utils.create_fulfillment_builder(
                    parameter_presets={
                        "confirm_text": None,
                    }
                ).proto_obj,
                target_page=utils.get_symbolic_page(
                    flow_obj.name,
                    utils.SymbolicPages.END_FLOW,
                ).name,
            )
        ]
    )

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100, "\n")
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
    # TODO: Remove this line after UAT verified
    test_flow.create_flow_pages(config)
