from django.db import models

# Create your models here.
class ImageFile(models.Model) :
    title = models.CharField(max_length=200)
    pubDate = models.DateTimeField('date published')
    type = models.TextField()
    dataList = models.TextField()

    def __str__(self):
        return self.title, self.type

    def summary(self):
        return self.dataList[:100]