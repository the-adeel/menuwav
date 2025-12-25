from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "username" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "role" VARCHAR(16) NOT NULL DEFAULT 'customer'
);
COMMENT ON COLUMN "user"."role" IS 'CUSTOMER: customer\nRESTAURANT_ADMIN: restaurant_admin\nSUPERADMIN: superadmin';
CREATE TABLE IF NOT EXISTS "restaurant" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "owner_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "menu" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "restaurant_id" INT NOT NULL REFERENCES "restaurant" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "menuitem" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "name" VARCHAR(255) NOT NULL,
    "description" TEXT,
    "price" DECIMAL(10,2) NOT NULL,
    "menu_id" INT NOT NULL REFERENCES "menu" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztmW1v2jAQx78KyqtO6iZgfVLfpUA31gITD1OltopMYsBq4lDbGUUV3322E5NnBi10MO"
    "UdnO+Su18u/p/hVXNcC9r0y4BCol2WXjUMHMg/xOzHJQ1Mp6FVGBgY2tLRUx5DyggwGbeN"
    "gE0hN1mQmgRNGXIxt2LPtoXRNbkjwuPQ5GH07EGDuWPIJjKP+0duRtiCL5Cqr9MnY4Sgbc"
    "XSRJa4t7QbbD6VtiZm19JR3G1omK7tOTh0ns7ZxMVLb4SZsI4hhgQwKC7PiCfSF9kFVaqK"
    "/ExDFz/FSIwFR8CzWaTcNRmYLhb8eDZUFjgWd/lcrZycn1x8PTu54C4yk6XlfOGXF9buB0"
    "oC7b62kOuAAd9DYgy5iacmP6fo1SaAZOOLxiQg8tSTEBWyf0rRAS+GDfGYTQS609MVzH7p"
    "3dp3vXvEvT6JWlzezH6Ht4Olqr8mwIYgp4DSmUsy2jAfZDRmOyCVISQZvoMHg5K4dk4/Nr"
    "DnSJRNnhPAJkwhVbEfh1MzPcpcx9/84lC12qDX77Qa3cuScnrA3Uavrw+6ertv6PVWs31Z"
    "IpAX4xGAmQEsB+EH3Bv8bHSDVepNec7Crr3hAVXO1ng+lbPcxyOWFgux7Y6eIhuIMAyB+T"
    "QDxDJiK5HHuCyLpp/mVRB8fdOFNpC80k8t0J7u8kL7+UosVBMqa7CBSWxu1c3jll5yqk7S"
    "AjAYy6zFvcWd0lAy5DqOLF+0SdyvkO4Dku5NZXu7kv1fKI0740UbGzVgNOTvbbgnJLfQiS"
    "kJSFBMI7x2CURjfAPnKcnO3ufVGWP/AObt8NxMwGy5p8Wag9fHq4LMfyv1Xk2vN7TFOsLp"
    "QOy9UzJb/BKHhXKnYilxZMikwpQvkI7yKKRxzzakQhp3ewgLDyUbdWEqrhDJjEn7nUp5qC"
    "eipF6mmuXtookYdLYgmk1+mcNiunPhlEhyxFPhWi2gSHkVIrpnG1YhojsV0WhmKZJ9+JLT"
    "hImwNwENmu3jN6gsfP3GXV/k7FD6bEepHbX0OwnUmQcrt532N+UeoVy77Vwlf3EnyMxo0D"
    "o0kQPsnF/cVUyCqeUHfQmC97NhVwCuN2rNln57VCkfVyVPThP5KqpIn5ST3Sm25s2Gu0hE"
    "MdbFzofvHOgO77yeHOUirbHpELfLAUaH/I2fZI0vwcrK4QWEPsXosmcv5arR5TckNFNz86"
    "eXSEgxwCxBildjA4iB+2ECrJTL6/xXWi7n/1laTmksvyODWWf+H71OOxtiJCQBcoB5gfcW"
    "MtlxyUaUPe4n1hUURdWrB8HkzCcouJSNibyKvMDVZv9Ib19eFn8AgtD3eg=="
)
