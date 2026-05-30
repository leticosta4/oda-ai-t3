import { Inject, Injectable, UnprocessableEntityException } from '@nestjs/common';
import { CACHE_MANAGER, Cache } from '@nestjs/cache-manager';
import { PrismaService } from '@/prisma/prisma.service';
import { CreateInstituicaoDto } from './dto/create-instituicao.dto';
import { UpdateInstituicaoDto } from './dto/update-instituicao.dto';
import { UUID } from 'node:crypto';
const INSTITUICOES_LIST_CACHE_KEY = 'instituicoes:list';

@Injectable()
export class InstituicaoService {
  constructor(
    private readonly prismaService: PrismaService,
    @Inject(CACHE_MANAGER)
    private readonly cacheManager: Cache,
  ) {}

  async create(createInstituicaoDto: CreateInstituicaoDto) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);

     
  
  return await this.prismaService.instituicao.create({data: createInstituicaoDto})
  }

  async findAll() {
    return this.cacheManager.wrap(INSTITUICOES_LIST_CACHE_KEY, async () =>
      await this.prismaService.instituicao.findMany({
        omit: {
          criadoEm: true,
          atualizadoEm: true,
        },
      }),
    );
  }

  async findOne(id: UUID) {
    return await this.prismaService.instituicao.findUniqueOrThrow({ where: { id }})
  }

  async update(id: UUID, updateInstituicaoDto: UpdateInstituicaoDto) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);
    return await this.prismaService.instituicao.update({ where: { id }, data: updateInstituicaoDto})
  }

  async remove(id: UUID) {
    await this.cacheManager.del(INSTITUICOES_LIST_CACHE_KEY);
    return await this.prismaService.instituicao.delete({where: { id }})
  }
}
