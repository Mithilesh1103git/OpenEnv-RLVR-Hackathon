import xml.etree.ElementTree as ET

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

    dict_keys = ["brand_name", "greetings", "message", "details"]

    for key in dict_keys:
        top_element_data = message.find(key)

        if key=="brand_name":
            parsed_dict["is_present"]["brand_name"] = True
            print(top_element_data)
            parsed_dict["raw_values"].append({"brand_name_value": top_element_data.text.strip()})

        if key=="greetings":
            parsed_dict["is_present"]["greetings"] = True
            
            greetings_prefix = top_element_data.find('prefix')
            if isinstance(greetings_prefix.text, str):
                parsed_dict["is_present"]["greetings_prefix"] = True
                parsed_dict["raw_values"].append({"greetings_prefix": greetings_prefix.text.strip()})
            
            greetings_username = top_element_data.find('username')
            if isinstance(greetings_username.text, str):
                parsed_dict["is_present"]["greetings_username"] = True
                parsed_dict["raw_values"].append({"greetings_username": greetings_username.text.strip()})

        if key=="message":
            parsed_dict["is_present"]["message"] = True
            parsed_dict["raw_values"].append({"message": top_element_data.text.strip()})

        if key=="details":
            parsed_dict["is_present"]["details"] = True
            details_all = top_element_data.findall("detail")
            
            for detail in details_all:
                detail_detail_category = detail.find("detail_category").text.strip()
                detail_type = detail.find("type").text.strip()
                detail_key = detail.find("key").text.strip()
                detail_value = detail.find("value").text.strip()
                
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

    print(f"parsed_msg_dict: {parsed_dict}")
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
            observations.append(f"Element '{key}_enclosures' found in message, therefore reward of {is_present_reward} was given.")
        else:
            default_reward = 0.5
            rewards_collected.append(default_reward)
            observations.append(f"Required '{key}_enclosures' was not found in message, therefore default reward of {default_reward} was given.")

    return rewards_collected, observations