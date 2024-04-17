import time

import agent_config
import anything_else
import authentication
import cancel_appointment
import confirm_block
import create_appointment
import default_start
import desired_action
import find_existing_appointment
import reschedule_appointment
import utils
import verify_appointment
import wrapup_block
from flows import office_hours
from resources.utils import Resources


def delete_flows(config):
    for flow in reversed(utils.FlowNames):
        utils.delete_flow_with_check(flow.value, config)


def create_flows(config):
    s = time.time()
    authentication.create_name_collection_flow_pages(config)
    e = time.time()
    print("time taken to create name collection flow pages: ", e - s)
    s = time.time()
    authentication.create_authentication_flow_pages(config)
    e = time.time()
    print("time taken to create authentication flow pages: ", e - s)
    s = time.time()
    find_existing_appointment.create_existing_appointment_flow_pages(config)
    e = time.time()
    print("time taken to create existing appointment flow pages: ", e - s)
    s = time.time()
    create_appointment.create_new_appointment_flow_pages(config)
    e = time.time()
    print("time taken to create new appointment flow pages: ", e - s)
    s = time.time()
    cancel_appointment.create_cancel_appointment_flow_pages(config)
    e = time.time()
    print("time taken to create cancel appointment flow pages: ", e - s)
    s = time.time()
    reschedule_appointment.create_reschedule_appointment_flow_pages(config)
    e = time.time()
    print("time taken to create reschedule appointment flow pages: ", e - s)
    s = time.time()
    verify_appointment.create_verify_appointment_flow_pages(config)
    e = time.time()
    print("time taken to create verify appointment flow pages: ", e - s)
    desired_action.create_desired_action_flow_pages(config)
    e = time.time()
    print("time taken to desired_action: ", e - s)
    s = time.time()
    office_hours.create_flow_pages(config)
    e = time.time()
    print("time taken to office_hours: ", e - s)
    s = time.time()
    default_start.create_default_start_flow_pages(config)
    e = time.time()
    print("time taken to default_start: ", e - s)
    s = time.time()
    confirm_block.create_confirm_block_flow_pages(config)
    e = time.time()
    print("time taken to confirm_block: ", e - s)
    s = time.time()
    anything_else.create_flow_pages(config)
    e = time.time()
    print("time taken to anything_else: ", e - s)
    s = time.time()
    wrapup_block.create_flow_pages(config)
    e = time.time()
    print("time taken to wrapup_block: ", e - s)


def main():
    s = time.time()
    config = utils.Config()
    if config.agent_display_name is None:
        raise ValueError("agent_display_name cannot be None")
    resource = Resources(config)
    resource.restore_agent()
    create_flows(config)
    agent_config.update_flow_settings(config)
    e = time.time()
    print("Total Time: ", e - s)


if __name__ == "__main__":
    main()
