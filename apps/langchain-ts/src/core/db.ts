import { PrismaClient, prismaConfig } from "@oda/database";
import * as dotenv from 'dotenv';
import * as path from 'path';
dotenv.config({ path: path.resolve(__dirname, '../../../../.env') });

export const prisma = new PrismaClient(prismaConfig);
