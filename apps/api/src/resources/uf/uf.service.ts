import { PrismaService } from '@/prisma/prisma.service';
import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { CreateUfDto } from './dto/create-uf.dto';
import { UpdateUfDto } from './dto/update-uf.dto';

const UF_LIST_CACHE_KEY = "uf:list"
@Injectable()
export class UfService {
    constructor(private readonly prismaService: PrismaService, @Inject(CACHE_MANAGER) private cacheManager: Cache){}

   
    async findAll(){
        return this.cacheManager.wrap(UF_LIST_CACHE_KEY, async () => 
        this.prismaService.estado.findMany(
            { 
                omit: {
                    criadoEm: true,
                    atualizadoEm: true,
                }
            }
        )
        )
    }
    async findById(id: string){
        return this.prismaService.estado.findUniqueOrThrow({
            where: {
                id
            }
        })
    }

    async findBySigla(sigla: string){
        return await this.prismaService.estado.findUniqueOrThrow({ where: { sigla}})
    }
  
}
