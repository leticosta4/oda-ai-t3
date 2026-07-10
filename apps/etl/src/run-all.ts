import * as fs from 'fs';
import * as path from 'path';
import * as dotenv from 'dotenv';

dotenv.config({
  path: path.resolve(__dirname, "../../../.env"),
});

import { saveGroupToDb } from './dgpEtl';
import { saveLattesToDb } from './lattesEtl';
import { PROCESSED_DATA_DIR } from './commom/config';

async function runAll() {
    console.log("=== RUNNING ETL FOR ALL GROUPS AND RESEARCHERS ===");
    
    const dgpDir = path.join(PROCESSED_DATA_DIR, 'dgp');
    const lattesDir = path.join(PROCESSED_DATA_DIR, 'lattes');

    if (!fs.existsSync(dgpDir)) {
        console.error(`DGP directory not found: ${dgpDir}`);
        return;
    }

    const groupFiles = fs.readdirSync(dgpDir).filter(f => f.endsWith('.json'));
    console.log(`Found ${groupFiles.length} groups in processed-data.`);

    for (const groupFile of groupFiles) {
        const groupFilePath = path.join(dgpDir, groupFile);
        console.log(`\n--------------------------------------------`);
        console.log(`[ETL-ALL] Processing Group: ${groupFile}`);
        
        const groupData = JSON.parse(fs.readFileSync(groupFilePath, 'utf-8'));
        
        // 1. Process group
        await saveGroupToDb(groupData);

        // 2. Process members
        if (groupData.membros && Array.isArray(groupData.membros)) {
            console.log(`[ETL-ALL] Group has ${groupData.membros.length} members. Checking files...`);
            for (const membro of groupData.membros) {
                if (!membro.lattes) continue;
                const lattesFileName = `${membro.lattes.trim()}.json`;
                const lattesFilePath = path.join(lattesDir, lattesFileName);

                if (fs.existsSync(lattesFilePath)) {
                    console.log(`[ETL-ALL] Processing Researcher Lattes: ${membro.nome} (${membro.lattes})`);
                    const lattesData = JSON.parse(fs.readFileSync(lattesFilePath, 'utf-8'));
                    await saveLattesToDb(lattesData);
                } else {
                    console.log(`[ETL-ALL] Lattes file NOT found for: ${membro.nome} (${membro.lattes})`);
                }
            }
        }
    }
    console.log("\n=== ETL RUN ALL COMPLETED ===");
}

runAll().catch(console.error);
