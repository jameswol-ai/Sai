import json
import os


class SaiMemory:


    def __init__(self):

        self.file="data/sai_memory.json"



    def save(self,event):


        os.makedirs(
            "data",
            exist_ok=True
        )


        history=[]


        if os.path.exists(
            self.file
        ):

            with open(
                self.file
            ) as f:

                history=json.load(f)



        history.append(event)



        with open(
            self.file,
            "w"
        ) as f:

            json.dump(
                history,
                f,
                indent=4
            )