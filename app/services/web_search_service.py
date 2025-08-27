from serpapi import GoogleSearch


class WebSearchService:
    def __init__(self, openai_client, web_search_api):
        self.openai_client = openai_client
        self.web_search_api = web_search_api

    def rephrase_query(self, user_question, chat_history):
        try:
            prompt = f"""
            Rephrase the following user question so it is clear, specific, and suitable for a web search.
            Previous chat:
            {chat_history}
            User question: {user_question}
            Rephrased web search query:
            """
            # Call GPT-3.5 or GPT-4o here
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error rephrasing query: {e}")
            return user_question  # Fallback to original question

    def do_web_search(self, query, num_results=4):
        try:
            params = {
                "q": query,
                "api_key": self.web_search_api,
                "num": num_results,
                "engine": "google"
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Check for errors in the response
            if "error" in results:
                print(f"Search API error: {results['error']}")
                return f"Search error: {results['error']}"
            
            # Extract top organic results
            organic_results = results.get("organic_results", [])
            if not organic_results:
                return "No search results found."
                
            formatted = []
            for r in organic_results:
                title = r.get("title", "")
                snippet = r.get("snippet", "")
                link = r.get("link", "")
                formatted.append(f"Title: {title}\nSnippet: {snippet}\nLink: {link}")
            return "\n\n".join(formatted)
        except Exception as e:
            print(f"Error in web search: {e}")
            return f"Search error: {str(e)}"
