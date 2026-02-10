import os
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI

# Define the schema that matches your PostgreSQL/Supabase table
class WildlifeSighting(BaseModel):
    species: str = Field(description="The common name of the animal sighted")
    scientific_name: Optional[str] = Field(description="The Latin name if mentioned or inferred")
    count: int = Field(description="The number of animals observed")
    health_status: str = Field(description="Description of the animal's condition (e.g., healthy, injured, juvenile)")
    location_context: str = Field(description="Specific landmarks or behavioral context mentioned")

# Initialize the client (Make sure to set your OPENAI_API_KEY environment variable)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def normalize_sighting_notes(raw_text: str):
    """
    Experiment: Extracting structured relational data from unstructured NPS-style notes.
    """
    print(f"--- Processing Raw Note ---\n'{raw_text}'\n")

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system", "content": "You are a data normalization assistant for wildlife biology. Extract information into a strict JSON format."},
            {"role": "user", "content": f"Extract sighting data from this note: {raw_text}"}
        ],
        response_format={"type": "json_object"}
    )

    return response.choices[0].message.content

# Test cases representing 'messy' API data from NPS or iNaturalist
test_notes = [
    "Spotted two adult bald eagles nesting near the western ridge. Both appeared healthy and active.",
    "Found a lone juvenile black bear scavenging near the campsite 4 dumpsters. Seemed underweight.",
    "Three elk observed crossing the main road at dusk. One had a noticeable limp in the rear left leg."
]

if __name__ == "__main__":
    for note in test_notes:
        structured_data = normalize_sighting_notes(note)
        print(f"Structured Result: {structured_data}\n")
