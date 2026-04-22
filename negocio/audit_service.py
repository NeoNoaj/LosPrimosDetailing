from persistencia.api_client import APIClient

class AuditService:
    @staticmethod
    def log_audit(user_id, action, ip, details):
        return APIClient.log_audit(user_id, action, ip, details)
