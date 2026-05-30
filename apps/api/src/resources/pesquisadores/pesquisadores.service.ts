import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { PrismaService } from '@/prisma/prisma.service';
import { CreatePesquisadoreDto } from './dto/create-pesquisadore.dto';
import { UpdatePesquisadoreDto } from './dto/update-pesquisadore.dto';

const PESQUISADORES_LIST_CACHE_KEY = 'pesquisadores:list';

@Injectable()
export class PesquisadoresService {
  constructor(
    private readonly prisma: PrismaService,
    @Inject(CACHE_MANAGER)
    private readonly cacheManager: Cache,
  ) {}

  async create(createPesquisadoreDto: CreatePesquisadoreDto) {
    await this.cacheManager.del(PESQUISADORES_LIST_CACHE_KEY);
    return 'This action adds a new pesquisadore';
  }

  async findAll() {
    return this.cacheManager.wrap(PESQUISADORES_LIST_CACHE_KEY, () =>
      this.prisma.pesquisador.findMany({
        omit: {
          criadoEm: true,
          atualizadoEm: true,
        },
      }),
    );
  }

  findOne(id: string) {
    return `This action returns a #${id} pesquisadore`;
  }

  async update(id: string, updatePesquisadoreDto: UpdatePesquisadoreDto) {
    await this.cacheManager.del(PESQUISADORES_LIST_CACHE_KEY);
    return `This action updates a #${id} pesquisadore`;
  }

  async remove(id: string) {
    await this.cacheManager.del(PESQUISADORES_LIST_CACHE_KEY);
    return `This action removes a #${id} pesquisadore`;
  }
}
