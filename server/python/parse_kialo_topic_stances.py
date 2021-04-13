id_to_stances = {}
if __name__ == "__main__":
    start = False
    data_path = "kialoData/should-a-license-be-required-in-order-to-have-a-child-procreate-2368_cleaned.txt"
    with open(data_path) as f:
        for line in f:
            if line.startswith("1. "):
                start = True
                topic = line.strip().split(" ",1)[1]
                id_to_stances["1."] = "pro"
                continue
            if start and line.strip() != "":
                parts = line.strip().split(" ",2)
                if len(parts) < 3:
                    continue
                #get parent claim stance
                _id = parts[0]
                parent_id  = ".".join(_id.split(".")[:-2]) + "."
                stance = parts[1].lower()[:-1]
                parent_stance = id_to_stances[parent_id]
                if parent_stance == stance:
                    id_to_stances[_id] = "pro"
                else:
                    id_to_stances[_id] = "con"
    
    fw = open("kialoData/should-a-license-be-required-in-order-to-have-a-child-procreate-2368_stances.txt", "w")
    for _id in id_to_stances:
        fw.write(_id + '\t' + id_to_stances[_id] + '\n')