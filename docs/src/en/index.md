# Lexiflux

## Features
- Utilizes aiobotocore for non-blocking IO operations.
- Supports recursive listing of "folders" with controllable depth control.
- Groups "folders" by prefixes to reduce the number of API calls.
- Handles S3 pagination to provide a efficient traversal of long S3 objects lists.
- Utilize AWS retry strategies.
- Allows processing objects as they are collected from AWS.

Read detailed explanation in [the blog post](https://sorokin.engineer/posts/en/aws_s3_async_list.html).

## Usage

### Simple
```python
--8<-- "list.py"
```
You can control the depth of recursion by specifying the `max_level` parameter, 
by default depth is not limited.

`max_folders` parameter allows you to group folders by prefix to reduce the number of API calls.

### Full async potential
Process objects asynchronously while gathering the objects list from AWS.

```python
async for page in S3BucketObjects(bucket='my-bucket').iter("my-prefix/", max_level=2, max_folders=10):
    for obj in page:
        print(obj['Key'])
```

## Docstrings
[S3BucketObjects][lexiflux]

