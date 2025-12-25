from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "order" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "table_number" INT,
    "status" VARCHAR(9) NOT NULL DEFAULT 'pending',
    "total" DECIMAL(10,2) NOT NULL DEFAULT 0,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "customer_id" INT REFERENCES "user" ("id") ON DELETE CASCADE,
    "restaurant_id" INT NOT NULL REFERENCES "restaurant" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "order"."status" IS 'PENDING: pending\nCONFIRMED: confirmed\nPREPARING: preparing\nREADY: ready\nCOMPLETED: completed\nCANCELLED: cancelled';
        CREATE TABLE IF NOT EXISTS "orderitem" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "quantity" INT NOT NULL DEFAULT 1,
    "price_at_time" DECIMAL(10,2) NOT NULL,
    "menu_item_id" INT NOT NULL REFERENCES "menuitem" ("id") ON DELETE CASCADE,
    "order_id" INT NOT NULL REFERENCES "order" ("id") ON DELETE CASCADE
);
        CREATE TABLE IF NOT EXISTS "qrcode" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "table_number" INT,
    "qr_type" VARCHAR(10) NOT NULL,
    "qr_data" VARCHAR(500) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "restaurant_id" INT NOT NULL REFERENCES "restaurant" ("id") ON DELETE CASCADE
);
COMMENT ON COLUMN "qrcode"."qr_type" IS 'TABLE: table\nRESTAURANT: restaurant';
        ALTER TABLE "user" ADD "email" VARCHAR(255);
        ALTER TABLE "user" ADD "phone" VARCHAR(20);
        ALTER TABLE "restaurant" ADD "address" TEXT;
        ALTER TABLE "restaurant" ADD "is_approved" BOOL NOT NULL DEFAULT False;
        ALTER TABLE "restaurant" ADD "email" VARCHAR(255);
        ALTER TABLE "restaurant" ADD "phone" VARCHAR(20);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "user" DROP COLUMN "email";
        ALTER TABLE "user" DROP COLUMN "phone";
        ALTER TABLE "restaurant" DROP COLUMN "address";
        ALTER TABLE "restaurant" DROP COLUMN "is_approved";
        ALTER TABLE "restaurant" DROP COLUMN "email";
        ALTER TABLE "restaurant" DROP COLUMN "phone";
        DROP TABLE IF EXISTS "order";
        DROP TABLE IF EXISTS "qrcode";
        DROP TABLE IF EXISTS "orderitem";"""


MODELS_STATE = (
    "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"
)
