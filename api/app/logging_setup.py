import json, logging, sys
class JsonFormatter(logging.Formatter):
    def format(self, record): return json.dumps({"level":record.levelname,"message":record.getMessage(),"logger":record.name})
def configure_logging():
    h=logging.StreamHandler(sys.stdout); h.setFormatter(JsonFormatter()); logging.basicConfig(level=logging.INFO,handlers=[h],force=True)
