from enum import Enum

from dfcx_scrapi.builders.pages import PageBuilder
from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.intents import Intents
from dfcx_scrapi.core.pages import Pages

import commons
import utils


class InnerPageNames(str, Enum):
    ASK_ANYTHING_ELSE = "> ask anything else"
    END_ESCALATE = "end escalate"


def create_flow_pages(
    config: utils.Config,
    flow_display_name="Anything Else",
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

    try:
        flow_display_name_wrapup_block = utils.FlowNames.WRAPUP_BLOCK
        flows_instance.get_flow_by_display_name(
            flow_display_name_wrapup_block, agent_id
        )
    except ValueError:
        flows_instance.create_flow(
            agent_id=agent_id, display_name=flow_display_name_wrapup_block
        )
        pass
    except Exception as e:
        utils.logger.error(e)
        raise

    pages_instance = Pages(creds_path=config.service_account_key)
    pages_to_create = [page.value for page in InnerPageNames]

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

    # Start Page
    flow_obj.transition_routes.clear()
    tr_extends = [
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            overwrite=True,
            target_page=page_map[InnerPageNames.ASK_ANYTHING_ELSE],
        )
    ]
    flow_obj.transition_routes.extend(tr_extends)

    # ask anything else page
    aae_page_obj = builder_map[InnerPageNames.ASK_ANYTHING_ELSE].proto_obj
    ee_page_name = page_map[InnerPageNames.END_ESCALATE]
    # Entry fulfillment
    aae_page_obj.entry_fulfillment = utils.create_fulfillment_builder(
        response_message={
            "message": commons.ANYTHING_ELSE_PROMPT,
            "type": "text",
        },
    ).proto_obj
    # event handlers
    aae_page_obj.event_handlers.clear()
    aae_page_obj.event_handlers.extend(
        [
            utils.create_event_handler(
                utils.EventNames.FLOW_FAILED_HUMAN_ESCALATION,
                None,
                ee_page_name,
            ),
            utils.create_event_handler(
                utils.EventNames.NO_INPUT_1,
                commons.ASK_ANYTHING_ELSE_NO_INPUT_1,
            ),
            utils.create_event_handler(
                utils.EventNames.NO_INPUT_2,
                commons.ASK_ANYTHING_ELSE_NO_INPUT_2,
                ee_page_name,
            ),
            utils.create_event_handler(
                utils.EventNames.NO_MATCH_1,
                commons.ASK_ANYTHING_ELSE_NO_MATCH_1,
            ),
            utils.create_event_handler(
                utils.EventNames.NO_MATCH_2,
                commons.ASK_ANYTHING_ELSE_NO_MATCH_2,
                ee_page_name,
            ),
        ]
    )
    # transition routes
    aae_page_trs = [
        # routes to default start flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[
                utils.IntentNames.PREBUILT_COMPONENTS_CONFIRMATION_YES
            ],
            target_flow=flows_map[utils.DEFAULT_START_FLOW],
        ),
        # routes to wrap-up block flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[
                utils.IntentNames.PREBUILT_COMPONENTS_CONFIRMATION_NO
            ],
            target_flow=flows_map[utils.FlowNames.WRAPUP_BLOCK],
        ),
        # routes to end escalate page
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[
                utils.IntentNames.PREBUILT_COMPONENTS_ESCALATE_HUMAN_AGENT
            ],
            target_page=page_map[InnerPageNames.END_ESCALATE],
        ),
        # routes to cancel flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[utils.IntentNames.APPOINTMENT_ROUTING_CANCEL],
            target_flow=flows_map[utils.FlowNames.CANCEL],
        ),
        # routes to verify flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[utils.IntentNames.APPOINTMENT_ROUTING_EXISTING],
            target_flow=flows_map[utils.FlowNames.VERIFY],
        ),
        # routes to create appointment flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[utils.IntentNames.APPOINTMENT_ROUTING_NEW_APP],
            target_flow=flows_map[utils.FlowNames.CREATE_NEW_APPOINTMENT],
        ),
        # routes to reschedule flow
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[
                utils.IntentNames.APPOINTMENT_ROUTING_RESCHEDULE
            ],
            target_flow=flows_map[utils.FlowNames.RESCHEDULE],
        ),
        # routes to end escalate page for billing
        TransitionRouteBuilder().create_new_proto_obj(
            intent=intents_map[utils.IntentNames.APPOINTMENT_ROUTING_BILLING],
            target_page=page_map[InnerPageNames.END_ESCALATE],
        ),
    ]
    aae_page_obj.transition_routes.clear()
    aae_page_obj.transition_routes.extend(aae_page_trs)
    builder_map[InnerPageNames.ASK_ANYTHING_ELSE].proto_obj = aae_page_obj

    # end escalate page
    ee_page_obj = builder_map[InnerPageNames.END_ESCALATE].proto_obj
    ee_page_obj.transition_routes.clear()
    ee_page_obj.transition_routes.extend(
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

    for page_display_name, builder in builder_map.items():
        print(page_map[page_display_name])
        print("-" * 100, "\n")
        pages_instance.update_page(
            page_id=page_map[page_display_name], obj=builder.proto_obj
        )

    flows_instance.update_flow(flow_id=flow_obj.name, obj=flow_obj)
