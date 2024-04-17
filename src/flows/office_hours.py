from enum import Enum

from dfcx_scrapi.builders.routes import TransitionRouteBuilder
from dfcx_scrapi.core.flows import Flows
from dfcx_scrapi.core.webhooks import Webhooks

import commons
import utils
from utils import FlowNames, create_flow_by_name


class InnerPageNames(str, Enum):
    CHECK_OFFICE_HOURS = "check office hours"
    END_ESCALATION = "end escalation"


def create_flow_pages(config):
    agent_id = utils.get_agent_id(config)
    flows_instance = Flows()
    flow_name = FlowNames.OFFICE_HOURS

    flow_obj, flows_instance, flows_map, pages_instance = create_flow_by_name(
        config=config, flow_name=flow_name, nlu_threshold=0.3
    )

    pages_to_create = [page.value for page in InnerPageNames]

    page_map, builder_map = utils.create_pages(
        pages_to_create, flow_obj, pages_instance, flows_map, flow_name
    )

    webhooks_instance = Webhooks(agent_id=agent_id)
    webhook_map = webhooks_instance.get_webhooks_map(
        agent_id=agent_id, reverse=True
    )

    coh_page_obj = builder_map[InnerPageNames.CHECK_OFFICE_HOURS].proto_obj
    coh_page_obj.entry_fulfillment = utils.create_fulfillment_builder(
        webhook=webhook_map[utils.WebHookNames.DIAGFLOW],
        tag="office_hours",
    ).proto_obj

    flow_obj.transition_routes.clear()
    tr_extends = [
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            overwrite=True,
            target_page=page_map[InnerPageNames.CHECK_OFFICE_HOURS],
        )
    ]
    flow_obj.transition_routes.extend(tr_extends)

    pac_open_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition='$session.params.is_pac_open = "true"',
        target_flow=flows_map[FlowNames.SCHEDULING],
        trigger_fulfillment=utils.create_fulfillment_builder(
            response_message={
                "message": commons.PROMPT_FOR_SCHEDULING,
                "type": "text",
            },
        ).proto_obj,
    )
    pac_closed_tr = TransitionRouteBuilder().create_new_proto_obj(
        condition='$session.params.is_pac_open != "true"',
        target_page=page_map[InnerPageNames.END_ESCALATION],
    )
    coh_page_obj.transition_routes.clear()
    coh_page_obj.transition_routes.extend([pac_open_tr, pac_closed_tr])
    coh_page_obj.event_handlers.clear()
    coh_page_obj.event_handlers.extend(
        [
            utils.create_event_handler(
                utils.EventNames.FLOW_FAILED,
                None,
                page_map[InnerPageNames.END_ESCALATION],
            ),
            utils.create_event_handler(
                utils.EventNames.FLOW_FAILED_HUMAN_ESCALATION,
                None,
                page_map[InnerPageNames.END_ESCALATION],
            ),
            utils.create_event_handler(
                utils.EventNames.WEBHOOK_ERROR,
                None,
                page_map[InnerPageNames.END_ESCALATION],
            ),
        ]
    )
    builder_map[InnerPageNames.CHECK_OFFICE_HOURS].proto_obj = coh_page_obj

    end_escalation_symbolic_transition = (
        TransitionRouteBuilder().create_new_proto_obj(
            condition="true",
            trigger_fulfillment=utils.create_fulfillment_builder(
                response_message={
                    "message": commons.OFFICE_HOURS_CLOSED,
                    "type": "text",
                },
            ).proto_obj,
            target_page=page_map[utils.SymbolicPages.END_SESSION],
        )
    )
    builder_map[
        InnerPageNames.END_ESCALATION
    ].proto_obj.transition_routes.extend(
        [
            end_escalation_symbolic_transition,
        ]
    )

    utils.update_flow_and_pages(
        flow_obj=flow_obj,
        page_map=page_map,
        builder_map=builder_map,
        pages_instance=pages_instance,
        flows_instance=flows_instance,
    )
