# Deployments

<!-- Instructions for Claude to build my deploy script -->

There should be a single command I can run to deploy all of these separate projects. The command would take arguments for which items need to be deployed. Ex if I touched the frontend and the backend both, I would want to deploy those both but not UpdatePhotoMetadata or UpdateBlogPostMetadata.

## frontend

### Build project

From the `frontend` directory, run the command:

```
npm run build
```

The build output will be placed in a folder named `build`.


### Update static site S3 objects

The site is hosted from S3 bucket `spark.wiki.frontend`.

Delete all objects in the bucket and replace them with the objects inside the `build` folder.

### Create a cache invalidation

In cloudfront distribution `E2JO5BSJ5WRP9P`, create a new cache invalidation for path `/*`.

## backend

From the `backend` directory, run the following commands to build and zip the source

```sh
rm -r .build
mkdir .build/packages
pip install --target .build/packages -r src/requirements.txt
cp src/*.py .build/packages
cp -r src/handlers/. .build/packages/handlers
cp -r src/utils/. .build/packages/utils

$compress = @{
  Path = ".build/packages/*"
  CompressionLevel = "Fastest"
  DestinationPath = ".build/lambda.zip"
}
Compress-Archive @compress -Force
```

This will leave a ZIP file at `backend/.build/lambda.zip`. Take this zip file and update the ContentAPI lambda to use this new zip as the source.

## ContentManagement/UpdatePhotoMetadata

Use the same process as for `backend`. The Lambda for UpdatePhotoMetadata is called `UpdatePhotoMetadata`.

After this, we'll need to run the script in `scripts/refreshPhotoMetadata.py` to retouch all photos and update them with whatever new metadata the update stores.

## ContentManagement/UpdateBlogPostMetadata

This is also a lambda. We'll update UpdateBlogPostMetadata with its new info. There's no `scripts/refreshBlogPostMetadata.py` but if there were, we'd need to run it.