from django.db import models
from django.contrib.auth.models import User

class SearchHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    query = models.CharField(max_length=255)
    
    # Store the actual product results as a list of dictionaries
    results_data = models.JSONField()
    
    # Auto-record the date and time of the search
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This ensures the newest searches appear first
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.username} searched for '{self.query}'"