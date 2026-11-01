from dotenv import load_dotenv
load_dotenv()
from app.parser import parse_mandate

m = parse_mandate("I want a desk lamp under $60, rated 4 stars or above, delivered within a week. Auto-buy if it is under $25.")
print(m.model_dump_json(indent=2))