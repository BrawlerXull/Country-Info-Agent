import httpx
from typing import Dict, Any, Optional

def fetch_country_info(country_name: str) -> Dict[str, Any]:
    """
    Fetches country information from the REST Countries API.
    
    Args:
        country_name: The name of the country to look up.
        
    Returns:
        A dictionary containing country data or an error message.
    """
    base_url = "https://restcountries.com/v3.1/name"
    
    try:
        # Use fullText=false by default to allow partial matches which are common, 
        # but the specific endpoint is /name/{name}
        # We handle the response carefully.
        url = f"{base_url}/{country_name}"
        
        with httpx.Client() as client:
            response = client.get(url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                # The API returns a list of matched countries. We'll take the first one 
                # that matches best or just the first one if multiple are returned.
                # Ideally, we could refine this, but for now, first match is reasonable.
                if isinstance(data, list) and len(data) > 0:
                    return {"status": "success", "data": data[0]}
                else:
                     return {"status": "error", "message": "No data found for this country."}
            elif response.status_code == 404:
                return {"status": "error", "message": f"Country '{country_name}' not found."}
            else:
                return {"status": "error", "message": f"API Error: {response.status_code}"}
                
    except httpx.RequestError as e:
        return {"status": "error", "message": f"Network error occurred: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
