import { Inject, Injectable } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { PrismaService } from '@/prisma/prisma.service';
import { CreateInstituicaoDto } from './dto/create-instituicao.dto';
import { UpdateInstituicaoDto } from './dto/update-instituicao.dto';

const INSTITUICOES_LIST_CACHE_KEY = 'instituicoes:list';

@Injectable()
export class InstituicaoService {
  constructor(
    private readonly prisma: PrismaService,
    @Inject(CACHE_MANAGER)
    private readonly cacheManager: Cache,
  ) {}

  async create(createInstituicaoDto: CreateInstituicaoDto) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);
    return 'This action adds a new instituicao';
  }

  async findAll() {
    return this.cacheManager.wrap(INSTITUICOES_LIST_CACHE_KEY, () =>
      this.prisma.instituicao.findMany({
        omit: {
          criadoEm: true,
          atualizadoEm: true,
        },
      }),
    );
  }

  findOne(id: string) {
    return `This action returns a #${id} instituicao`;
  }

  async update(id: string, updateInstituicaoDto: UpdateInstituicaoDto) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);
    return `This action updates a #${id} instituicao`;
  }

  async remove(id: string) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);
    return `This action removes a #${id} instituicao`;
  }
}
