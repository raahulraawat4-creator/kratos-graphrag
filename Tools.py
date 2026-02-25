
class Neo4jTool:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def run(self, query: str, params: dict = None):
        with self.driver.session() as session:
            result = session.run(query, params or {}, timeout=5000)
            return [record.data() for record in result]

    def close(self):
        self.driver.close()
