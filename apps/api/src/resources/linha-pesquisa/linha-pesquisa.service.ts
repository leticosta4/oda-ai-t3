import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { PrismaService } from '@/prisma/prisma.service';
import { CreateLinhaPesquisaDto } from './dto/create-linha-pesquisa.dto';
import { UpdateLinhaPesquisaDto } from './dto/update-linha-pesquisa.dto';

const LINHAS_PESQUISA_LIST_CACHE_KEY = 'linhas-pesquisa:list';

@Injectable()
export class LinhaPesquisaService {
  constructor(
    private readonly prisma: PrismaService,
    @Inject(CACHE_MANAGER)
    private readonly cacheManager: Cache,
  ) {}

  async create(createLinhaPesquisaDto: CreateLinhaPesquisaDto) {
    await this.cacheManager.del(LINHAS_PESQUISA_LIST_CACHE_KEY);
    return 'This action adds a new linhaPesquisa';
  }

  async findAll() {
    return this.cacheManager.wrap(LINHAS_PESQUISA_LIST_CACHE_KEY, () =>
      this.prisma.linhaPesquisa.findMany({
        omit: {
          criadoEm: true,
          atualizadoEm: true,
        },
      }),
    );
  }

  findOne(id: string) {
    return `This action returns a #${id} linhaPesquisa`;
  }

  async update(id: string, updateLinhaPesquisaDto: UpdateLinhaPesquisaDto) {
    await this.cacheManager.del(LINHAS_PESQUISA_LIST_CACHE_KEY);
    return `This action updates a #${id} linhaPesquisa`;
  }

  async remove(id: string) {
    await this.cacheManager.del(LINHAS_PESQUISA_LIST_CACHE_KEY);
    return `This action removes a #${id} linhaPesquisa`;
  }
}
