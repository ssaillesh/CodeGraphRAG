from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


class LocalModelLoader:
    def __init__(self, model_name: str, device_map: str = "auto"):
        self.model_name = model_name
        self.device_map = device_map
        self._pipeline = None

    @property
    def text_generation_pipeline(self):
        if self._pipeline is None:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForCausalLM.from_pretrained(self.model_name, device_map=self.device_map)
            self._pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=900,
                do_sample=False,
            )
        return self._pipeline

    def generate(self, prompt: str) -> str:
        output = self.text_generation_pipeline(prompt)
        return output[0]["generated_text"]
