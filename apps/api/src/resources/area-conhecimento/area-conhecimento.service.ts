import { PrismaService } from '@/prisma/prisma.service';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { Inject, Injectable } from '@nestjs/common';
import { CreateAreaConhecimentoDto } from './dto/create-area-conhecimento.dto';
import { UpdateAreaConhecimentoDto } from './dto/update-area-conhecimento.dto';

const AREA_CONHECIMENTO_LIST_KEY = 'areaconhecimento:list';

@Injectable()
export class AreaConhecimentoService {
     constructor(
        private readonly prismaService: PrismaService,
        @Inject(CACHE_MANAGER)
        private readonly cacheManager: Cache,
      ) {}
      
      async create(createAreaConhecimento: CreateAreaConhecimentoDto) {
        await this.cacheManager.del(AREA_CONHECIMENTO_LIST_KEY);
        const nomeNormalizado = this.normalizeString(createAreaConhecimento.nome);
        return await this.prismaService.areaConhecimento.create({
          data: {
            ...createAreaConhecimento,
            nomeNormalizado,
          }
        });
      }
    
      async findAll() {
        return this.cacheManager.wrap(AREA_CONHECIMENTO_LIST_KEY,async () =>
          await this.prismaService.areaConhecimento.findMany({
            omit: {
              criadoEm: true,
              atualizadoEm: true,
            },
          }),
        );
      }
      
      
      async findById(id: string) {
        return await this.prismaService.areaConhecimento.findUnique({ where: { id: id}})
      }
    

      async update(id: string, updateAreaConhecimento: UpdateAreaConhecimentoDto){
        const updateData: any = { ...updateAreaConhecimento };
        if (updateAreaConhecimento.nome) {
          updateData.nomeNormalizado = this.normalizeString(updateAreaConhecimento.nome);
        }
        return await this.prismaService.areaConhecimento.update({ where: { id}, data: updateData})
      }

      private normalizeString(str: string): string {
        if (!str) return '';
        const stopwords = new Set([
            'de', 'do', 'da', 'dos', 'das', 'em', 'um', 'uma', 'uns', 'umas', 
            'para', 'com', 'por', 'sem', 'sob', 'sobre', 'a', 'o', 'as', 'os', 'e',
            'of', 'the', 'in', 'on', 'at', 'for', 'with', 'by', 'a', 'an', 'and', 'to', 'from', 'about'
        ]);
        const words = str
            .trim()
            .toLowerCase()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/[^a-z0-9\s]/g, ' ')
            .replace(/\s+/g, ' ')
            .split(' ');
        return words
            .filter(word => word.length > 0 && !stopwords.has(word))
            .join('-');
      }
}
