
def parse_llm_response(message: str):
    parsed_dict = {
        "is_present": {
            "brand_name": False,
            "greetings": False,
            "greetings_prefix": False,
            "greetings_username": False,
            "message": False,
            "details": False,
            "assignment_title": False,
            "deadline": False,
            "lms_link": False,
            "associated_lecture_link": False,
            "youtube_lecture_link": False,
        },
        "raw_values": []
    }

    root_dict_node = message['notification']
    if not root_dict_node:
        return parsed_dict

    sample_dict_keys = ["brand_name", "greetings", "message", "details"]

    for key in sample_dict_keys:

        if key=="brand_name":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["brand_name"] = True

        if key=="greetings":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["greetings"] = True

                greetings_prefix = main_key_node['prefix']
                if greetings_prefix:
                    parsed_dict["is_present"]["greetings_prefix"] = True
                    # parsed_dict["raw_values"].append({"greetings_prefix": greetings_prefix.text.strip()})
                
                greetings_prefix = main_key_node['username']
                if greetings_prefix:
                    parsed_dict["is_present"]["greetings_username"] = True

        if key=="message":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["message"] = True

        if key=="details":
            main_key_node = root_dict_node[key]
            if main_key_node:
                parsed_dict["is_present"]["details"] = True

                for detail in main_key_node:

                    detail_detail_category = detail["category"]
                    detail_type = detail["type"]
                    detail_key = detail["label"]
                    detail_value = detail["value"]
                    
                    if detail_type=="assignment_title":
                        parsed_dict["is_present"]["assignment_title"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type=="deadline":
                        parsed_dict["is_present"]["deadline"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type=="lms_link":
                        parsed_dict["is_present"]["lms_link"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type=="associated_lecture_link":
                        parsed_dict["is_present"]["associated_lecture_link"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})
                    if detail_type=="youtube_lecture_link":
                        parsed_dict["is_present"]["youtube_lecture_link"] = True
                        parsed_dict["raw_values"].append({detail_key: detail_value})

    return parsed_dict

def reward_collection(parsed_dict: dict):
    rewards_collected = []
    observations = []

    is_present_keys = parsed_dict['is_present'].keys()
    for key in list(is_present_keys):
        is_present_value = parsed_dict['is_present'][key]
        if is_present_value:
            is_present_reward = 5
            rewards_collected.append(is_present_reward)
            observations.append(f"Element '{key}_is_present' found in message, therefore reward of {is_present_reward} was given.")
        else:
            default_reward = 0.5
            rewards_collected.append(default_reward)
            observations.append(f"Required '{key}_is_present' was not found in message, therefore default reward of {default_reward} was given.")

    return rewards_collected, observations